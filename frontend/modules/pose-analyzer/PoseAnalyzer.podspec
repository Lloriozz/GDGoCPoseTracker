Pod::Spec.new do |s|
  s.name           = 'PoseAnalyzer'
  s.version        = '1.0.0'
  s.summary        = 'On-device pose analysis using Vision + CoreML'
  s.description    = 'Expo native module: VNDetectHumanBodyPoseRequest + CoreML classifiers for 4 exercises'
  s.homepage       = 'https://github.com/placeholder'
  s.license        = 'MIT'
  s.author         = 'GDGoC'
  s.platform       = :ios, '14.0'
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'

  s.source_files = 'ios/*.swift'
  s.resources    = ['ios/Models/**']

  s.frameworks   = 'Vision', 'CoreML', 'UIKit'
  s.swift_version = '5.5'
end
