import ExpoModulesCore
import Vision
import CoreML
import UIKit
import AVFoundation

// MARK: - PoseAnalyzerModule
public class PoseAnalyzerModule: Module {

  // CoreML models — lazy loaded once on first use
  private var bicepModel: MLModel?
  private var squatModel: MLModel?
  private var lungeStageModel: MLModel?
  private var lungeErrModel: MLModel?
  private var plankModel: MLModel?

  private let modelQueue = DispatchQueue(label: "pose.coreml", qos: .userInteractive)

  public func definition() -> ModuleDefinition {
    Name("PoseAnalyzer")

    // Load all CoreML models on a background thread so we don't block TurboModule init
    OnCreate {
      self.modelQueue.async { self.loadModels() }
    }

    // analyzeFrame(base64Jpeg, exercise) → Promise<Result>
    AsyncFunction("analyzeFrame") { (base64: String, exercise: String, promise: Promise) in
      guard let data = Data(base64Encoded: base64, options: .ignoreUnknownCharacters),
            let uiImage = UIImage(data: data),
            let cgImage = uiImage.cgImage else {
        promise.resolve(["error": "Invalid image"])
        return
      }

      self.modelQueue.async {
        let landmarks = self.detectPose(cgImage: cgImage, orientation: self.imageOrientation(uiImage))
        guard !landmarks.isEmpty else {
          promise.resolve(["landmarks": [], "correction": "No pose detected", "isCorrect": false, "counter": 0, "score": 0])
          return
        }

        // Run exercise classifier
        let result = self.classify(landmarks: landmarks, exercise: exercise)
        var out = result
        out["landmarks"] = landmarks.map { lm in
          ["x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility]
        }
        promise.resolve(out)
      }
    }
  }

  // MARK: - Load CoreML Models
  private func loadModels() {
    // Resources are bundled inside the pod's bundle (PoseAnalyzer.bundle)
    // When using static_framework the resources land in the main bundle.
    let bundle = Bundle(for: PoseAnalyzerModule.self)
    // Also check a sub-bundle named "PoseAnalyzer" (CocoaPods resource_bundle)
    let podBundle = bundle.url(forResource: "PoseAnalyzer", withExtension: "bundle")
                         .flatMap { Bundle(url: $0) } ?? bundle

    func load(_ name: String) -> MLModel? {
      for b in [podBundle, bundle, Bundle.main] {
        if let url = b.url(forResource: name, withExtension: "mlpackage") ??
                     b.url(forResource: name, withExtension: "mlmodelc") {
          if let model = try? MLModel(contentsOf: url) { return model }
        }
      }
      print("[PoseAnalyzer] ⚠️ Could not load model: \(name)")
      return nil
    }
    bicepModel      = load("bicep_posture")
    squatModel      = load("squat_stage")
    lungeStageModel = load("lunge_stage")
    lungeErrModel   = load("lunge_error")
    plankModel      = load("plank_posture")
    print("[PoseAnalyzer] Models loaded — bicep:\(bicepModel != nil) squat:\(squatModel != nil) lunge:\(lungeStageModel != nil) plank:\(plankModel != nil)")
  }

  // MARK: - Vision Pose Detection
  private struct Landmark {
    let x: Float; let y: Float; let z: Float; let visibility: Float
  }

  private func detectPose(cgImage: CGImage, orientation: CGImagePropertyOrientation) -> [Landmark] {
    var result: [Landmark] = []
    let semaphore = DispatchSemaphore(value: 0)

    let request = VNDetectHumanBodyPoseRequest { req, _ in
      defer { semaphore.signal() }
      guard let obs = req.results?.first as? VNHumanBodyPoseObservation else { return }
      result = self.parsePose(obs)
    }

    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: orientation)
    try? handler.perform([request])
    semaphore.wait()
    return result
  }

  // Map Apple Vision 19 joints → 33-slot MediaPipe array
  // Unmapped slots stay at (0, 0, 0, 0)
  private func parsePose(_ obs: VNHumanBodyPoseObservation) -> [Landmark] {
    var lms = Array(repeating: Landmark(x: 0, y: 0, z: 0, visibility: 0), count: 33)

    func set(_ mpIdx: Int, _ joint: VNHumanBodyPoseObservation.JointName) {
      guard let pt = try? obs.recognizedPoint(joint), pt.confidence > 0.1 else { return }
      // Vision coords: origin bottom-left, y flipped; convert to top-left
      lms[mpIdx] = Landmark(x: Float(pt.x), y: Float(1 - pt.y), z: 0, visibility: Float(pt.confidence))
    }

    // Head
    set(0,  .nose)
    set(2,  .leftEye)
    set(5,  .rightEye)
    set(7,  .leftEar)
    set(8,  .rightEar)
    // Upper body
    set(11, .leftShoulder)
    set(12, .rightShoulder)
    set(13, .leftElbow)
    set(14, .rightElbow)
    set(15, .leftWrist)
    set(16, .rightWrist)
    // Lower body
    set(23, .leftHip)
    set(24, .rightHip)
    set(25, .leftKnee)
    set(26, .rightKnee)
    set(27, .leftAnkle)
    set(28, .rightAnkle)

    return lms
  }

  // MARK: - CoreML Classification
  private func classify(landmarks: [Landmark], exercise: String) -> [String: Any] {
    switch exercise {
    case "bicep_curl":  return runBicep(landmarks)
    case "squat":       return runSquat(landmarks)
    case "lunge":       return runLunge(landmarks)
    case "plank":       return runPlank(landmarks)
    default:            return ["correction": "Unknown exercise", "isCorrect": false, "counter": 0, "score": 0]
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  /// Extract (x,y,z,v) × n landmarks into flat MLMultiArray
  private func featuresArray(landmarks: [Landmark], indices: [Int]) -> MLMultiArray? {
    let n = indices.count * 4
    guard let arr = try? MLMultiArray(shape: [NSNumber(value: n)], dataType: .float32) else { return nil }
    for (i, idx) in indices.enumerated() {
      let lm = landmarks[idx]
      arr[i*4+0] = NSNumber(value: lm.x)
      arr[i*4+1] = NSNumber(value: lm.y)
      arr[i*4+2] = NSNumber(value: lm.z)
      arr[i*4+3] = NSNumber(value: lm.visibility)
    }
    return arr
  }

  private func predict(model: MLModel?, features: MLMultiArray) -> (label: String, prob: Double) {
    guard let model = model else { return ("?", 0) }
    let input = try? MLDictionaryFeatureProvider(dictionary: ["features": features])
    guard let input = input,
          let output = try? model.prediction(from: input),
          let label = output.featureValue(for: "label")?.stringValue else { return ("?", 0) }
    let prob = output.featureValue(for: "labelProbability")?.dictionaryValue[label] as? Double ?? 0
    return (label, prob)
  }

  private func angle(_ a: Landmark, _ b: Landmark, _ c: Landmark) -> Float {
    let rad = atan2(c.y - b.y, c.x - b.x) - atan2(a.y - b.y, a.x - b.x)
    var deg = abs(rad * 180 / .pi)
    if deg > 180 { deg = 360 - deg }
    return deg
  }

  // ── Bicep ─────────────────────────────────────────────────────────────────
  // 9 landmarks: NOSE(0), L_SH(11), R_SH(12), R_EL(14), L_EL(13),
  //              R_WR(16), L_WR(15), L_HIP(23), R_HIP(24)
  private var bicepCounter = 0
  private var bicepStage = "down"

  private func runBicep(_ lms: [Landmark]) -> [String: Any] {
    let rSh = lms[12]; let rEl = lms[14]; let rWr = lms[16]
    guard rSh.visibility > 0.5 else {
      return ["correction": "Stand fully in frame!", "isCorrect": false, "counter": bicepCounter, "score": 0]
    }

    let curlAngle = angle(rSh, rEl, rWr)
    if curlAngle > 120 { bicepStage = "down" }
    else if curlAngle < 90 && bicepStage == "down" { bicepStage = "up"; bicepCounter += 1 }

    guard let arr = featuresArray(landmarks: lms, indices: [0,11,12,14,13,16,15,23,24]) else {
      return ["correction": "...", "isCorrect": true, "counter": bicepCounter, "score": 0]
    }
    let (label, prob) = predict(model: bicepModel, features: arr)
    let isCorrect = label == "C"
    let correction = isCorrect ? "Good form! (\(Int(curlAngle))°)" : "Don't lean back!"
    return ["correction": correction, "isCorrect": isCorrect, "counter": bicepCounter, "score": Int(prob * 100)]
  }

  // ── Squat ─────────────────────────────────────────────────────────────────
  // 9 landmarks: NOSE(0), L_SH(11), R_SH(12), L_HIP(23), R_HIP(24),
  //              L_KN(25), R_KN(26), L_AN(27), R_AN(28)
  private var squatCounter = 0
  private var squatStage = ""

  private func runSquat(_ lms: [Landmark]) -> [String: Any] {
    guard let arr = featuresArray(landmarks: lms, indices: [0,11,12,23,24,25,26,27,28]) else {
      return ["correction": "...", "isCorrect": true, "counter": squatCounter, "score": 0]
    }
    let (stage, prob) = predict(model: squatModel, features: arr)
    if stage == "down" && prob > 0.65 { squatStage = "down" }
    else if squatStage == "down" && stage == "up" && prob > 0.65 { squatStage = "up"; squatCounter += 1 }

    // Feet/knee placement
    let lSh = lms[11]; let rSh = lms[12]
    let lKn = lms[25]; let rKn = lms[26]
    let lAn = lms[27]; let rAn = lms[28]
    let shW = sqrt(pow(rSh.x - lSh.x, 2) + pow(rSh.y - lSh.y, 2))
    let ftW = sqrt(pow(rAn.x - lAn.x, 2) + pow(rAn.y - lAn.y, 2))
    let knW = sqrt(pow(rKn.x - lKn.x, 2) + pow(rKn.y - lKn.y, 2))

    var correction = "Perfect form!"
    var isCorrect = true
    if shW > 0.001 {
      let fsr = ftW / shW
      if fsr < 1.2 { correction = "Stand wider!"; isCorrect = false }
      else if fsr > 2.8 { correction = "Bring feet closer!"; isCorrect = false }
      else if ftW > 0.001 {
        let kfr = knW / ftW
        if kfr < 0.5 { correction = "Push knees out!"; isCorrect = false }
        else if kfr > 1.1 { correction = "Keep knees over toes!"; isCorrect = false }
      }
    }
    return ["correction": correction, "isCorrect": isCorrect, "counter": squatCounter, "score": Int(prob * 100), "stage": squatStage]
  }

  // ── Lunge ─────────────────────────────────────────────────────────────────
  // 13 landmarks: 0,11,12,23,24,25,26,27,28,29,30,31,32
  private var lungeCounter = 0
  private var lungeStage = "init"

  private func runLunge(_ lms: [Landmark]) -> [String: Any] {
    let indices = [0,11,12,23,24,25,26,27,28,29,30,31,32]
    guard let arr = featuresArray(landmarks: lms, indices: indices) else {
      return ["correction": "...", "isCorrect": true, "counter": lungeCounter, "score": 0]
    }
    let (stagePred, stageProb) = predict(model: lungeStageModel, features: arr)

    if stagePred == "D" && stageProb > 0.7 { lungeStage = "down" }
    else if stagePred == "M" && stageProb > 0.7 { lungeStage = "mid" }
    else if stagePred == "I" && stageProb > 0.7 {
      if lungeStage == "down" || lungeStage == "mid" { lungeCounter += 1 }
      lungeStage = "init"
    }

    var correction = lungeStage == "down" ? "Good lunge!" : "Ready..."
    var isCorrect = true

    if lungeStage == "down" {
      let (errLabel, errProb) = predict(model: lungeErrModel, features: arr)
      if errLabel == "L" && errProb > 0.7 {
        correction = "Knee over toe!"; isCorrect = false
      } else {
        let lVis = min(lms[23].visibility, lms[25].visibility, lms[27].visibility)
        let rVis = min(lms[24].visibility, lms[26].visibility, lms[28].visibility)
        if lVis > 0.5 {
          let lAng = angle(lms[23], lms[25], lms[27])
          if lAng < 60 || lAng > 125 { correction = "Left knee: aim for 90°!"; isCorrect = false }
        }
        if rVis > 0.5 {
          let rAng = angle(lms[24], lms[26], lms[28])
          if rAng < 60 || rAng > 125 { correction = "Right knee: aim for 90°!"; isCorrect = false }
        }
      }
    }
    return ["correction": correction, "isCorrect": isCorrect, "counter": lungeCounter, "score": Int(stageProb * 100), "stage": lungeStage]
  }

  // ── Plank ─────────────────────────────────────────────────────────────────
  // 17 landmarks: 0,11–16,23–28,29–32
  private var plankCounter = 0

  private func runPlank(_ lms: [Landmark]) -> [String: Any] {
    let coreVis = min(lms[11].visibility, lms[12].visibility, lms[23].visibility, lms[24].visibility)
    guard coreVis > 0.5 else {
      return ["correction": "Show your back and hips!", "isCorrect": false, "counter": plankCounter, "score": 0]
    }
    let indices = [0,11,12,13,14,15,16,23,24,25,26,27,28,29,30,31,32]
    guard let arr = featuresArray(landmarks: lms, indices: indices) else {
      return ["correction": "...", "isCorrect": true, "counter": plankCounter, "score": 0]
    }
    let (label, prob) = predict(model: plankModel, features: arr)
    var correction = "Perfect plank! Hold it!"
    var isCorrect = true
    if label == "L" && prob > 0.6 { correction = "Sagging back! Tighten core."; isCorrect = false }
    else if label == "H" && prob > 0.6 { correction = "Hips too high! Lower them."; isCorrect = false }
    return ["correction": correction, "isCorrect": isCorrect, "counter": plankCounter, "score": Int(prob * 100)]
  }

  // MARK: - Helpers
  private func imageOrientation(_ img: UIImage) -> CGImagePropertyOrientation {
    switch img.imageOrientation {
    case .up:            return .up
    case .down:          return .down
    case .left:          return .left
    case .right:         return .right
    case .upMirrored:    return .upMirrored
    case .downMirrored:  return .downMirrored
    case .leftMirrored:  return .leftMirrored
    case .rightMirrored: return .rightMirrored
    @unknown default:    return .up
    }
  }
}
