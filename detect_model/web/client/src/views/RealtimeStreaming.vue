<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const apiUrl = import.meta.env.VITE_BASE_URL || window.location.origin;
const EXERCISES = ["squat", "plank", "bicep_curl", "lunge"];
const CAPTURE_INTERVAL_MS = 700;

const selectedExercise = ref("squat");
const videoRef = ref(null);
const canvasRef = ref(null);
const sessionId = ref(null);
const isRunning = ref(false);
const isCameraReady = ref(false);
const isRequestInFlight = ref(false);
const errorMessage = ref("");
const statusMessage = ref("Allow camera access to start live pose tracking.");
const result = ref({
    score: 0,
    rep_count: 0,
    correction: "Waiting for pose data...",
    is_correct: true,
    landmarks: [],
});

let mediaStream = null;
let timeoutId = null;

const skeletonColor = computed(() =>
    result.value.is_correct ? "#41b883" : "#ef4444"
);

const connections = [
    [11, 12],
    [11, 13], [13, 15],
    [12, 14], [14, 16],
    [11, 23], [12, 24],
    [23, 24],
    [23, 25], [25, 27],
    [24, 26], [26, 28],
    [0, 11], [0, 12],
];

const drawSkeleton = () => {
    const canvas = canvasRef.value;
    const video = videoRef.value;
    if (!canvas || !video) return;

    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    const landmarks = result.value.landmarks || [];
    if (!landmarks.length) return;

    ctx.strokeStyle = skeletonColor.value;
    ctx.lineWidth = 3;
    ctx.fillStyle = skeletonColor.value;

    connections.forEach(([start, end]) => {
        const p1 = landmarks[start];
        const p2 = landmarks[end];
        if (!p1 || !p2) return;

        ctx.beginPath();
        ctx.moveTo((1 - p1.x) * width, p1.y * height);
        ctx.lineTo((1 - p2.x) * width, p2.y * height);
        ctx.stroke();
    });

    landmarks.forEach((point) => {
        ctx.beginPath();
        ctx.arc((1 - point.x) * width, point.y * height, 4, 0, Math.PI * 2);
        ctx.fill();
    });
};

watch(
    () => result.value.landmarks,
    () => {
        drawSkeleton();
    },
    { deep: true }
);

const scheduleNextFrame = (delay = CAPTURE_INTERVAL_MS) => {
    clearTimeout(timeoutId);
    if (!isRunning.value) return;
    timeoutId = setTimeout(() => {
        void analyzeCurrentFrame();
    }, delay);
};

const stopRealtime = async () => {
    isRunning.value = false;
    clearTimeout(timeoutId);

    if (sessionId.value) {
        try {
            await fetch(`${apiUrl}/api/pose/close/?session_id=${sessionId.value}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
            });
        } catch (error) {
            console.error("Failed to close pose session", error);
        }
    }

    sessionId.value = null;
};

const analyzeCurrentFrame = async () => {
    if (!isRunning.value || isRequestInFlight.value) return;
    if (!videoRef.value || !canvasRef.value) return;

    const video = videoRef.value;
    if (!video.videoWidth || !video.videoHeight) {
        scheduleNextFrame(1000);
        return;
    }

    isRequestInFlight.value = true;
    errorMessage.value = "";

    try {
        const captureCanvas = document.createElement("canvas");
        captureCanvas.width = video.videoWidth;
        captureCanvas.height = video.videoHeight;
        const captureContext = captureCanvas.getContext("2d");
        captureContext.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);

        const frame = captureCanvas.toDataURL("image/jpeg", 0.5);
        const params = new URLSearchParams({ type: selectedExercise.value });
        if (sessionId.value) {
            params.set("session_id", sessionId.value);
        }

        const response = await fetch(`${apiUrl}/api/pose/analyze/?${params.toString()}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ frame }),
        });

        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "Pose analysis failed.");
        }

        sessionId.value = payload.session_id || sessionId.value;
        statusMessage.value =
            payload.type === "no_detection"
                ? "No full body detected"
                : `Tracking ${selectedExercise.value.replace("_", " ")}`;

        result.value = {
            score: payload.score ?? 0,
            rep_count: payload.rep_count ?? 0,
            correction: payload.correction || payload.message || "Waiting for pose data...",
            is_correct: payload.is_correct ?? false,
            landmarks: payload.landmarks || [],
        };

        scheduleNextFrame();
    } catch (error) {
        console.error(error);
        errorMessage.value =
            error instanceof Error ? error.message : "Unable to reach pose backend.";
        statusMessage.value = "Realtime tracking stopped";
        isRunning.value = false;
    } finally {
        isRequestInFlight.value = false;
    }
};

const startRealtime = async () => {
    if (!isCameraReady.value) {
        errorMessage.value = "Camera is not ready yet.";
        return;
    }

    await stopRealtime();
    result.value = {
        score: 0,
        rep_count: 0,
        correction: "Starting realtime pose tracking...",
        is_correct: true,
        landmarks: [],
    };
    statusMessage.value = "Starting realtime pose tracking...";
    errorMessage.value = "";
    isRunning.value = true;
    void analyzeCurrentFrame();
};

const setupCamera = async () => {
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 960 },
                height: { ideal: 720 },
                facingMode: "user",
            },
            audio: false,
        });

        if (videoRef.value) {
            videoRef.value.srcObject = mediaStream;
            await videoRef.value.play();
            isCameraReady.value = true;
            statusMessage.value = "Camera ready. Pick an exercise and start.";
        }
    } catch (error) {
        console.error(error);
        errorMessage.value =
            "Browser camera permission was denied or is unavailable in this environment.";
        statusMessage.value = "Camera unavailable";
    }
};

onMounted(() => {
    void setupCamera();
});

onBeforeUnmount(async () => {
    await stopRealtime();
    if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
        mediaStream = null;
    }
});
</script>

<template>
    <section class="realtime-page">
        <div class="panel controls">
            <h2>Realtime Tracking</h2>
            <p class="helper">
                This browser demo sends camera frames to the same deployed pose API used by the Expo app.
            </p>

            <div class="exercise-grid">
                <button
                    v-for="exercise in EXERCISES"
                    :key="exercise"
                    class="exercise-btn"
                    :class="{ active: selectedExercise === exercise }"
                    @click="selectedExercise = exercise"
                >
                    {{ exercise.replace("_", " ") }}
                </button>
            </div>

            <div class="action-row">
                <button class="primary-btn" @click="startRealtime">
                    Start Realtime
                </button>
                <button class="secondary-btn" @click="stopRealtime">
                    Stop
                </button>
            </div>

            <p class="status">{{ statusMessage }}</p>
            <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

            <div class="metrics">
                <div class="metric-card">
                    <span>Score</span>
                    <strong>{{ result.score }}</strong>
                </div>
                <div class="metric-card">
                    <span>Reps</span>
                    <strong>{{ result.rep_count }}</strong>
                </div>
            </div>

            <div class="feedback" :class="{ bad: !result.is_correct }">
                {{ result.correction }}
            </div>
        </div>

        <div class="panel camera-panel">
            <div class="camera-stage">
                <video ref="videoRef" playsinline muted></video>
                <canvas ref="canvasRef" class="overlay"></canvas>
            </div>
        </div>
    </section>
</template>

<style lang="scss" scoped>
.realtime-page {
    display: grid;
    grid-template-columns: minmax(280px, 360px) 1fr;
    gap: 1.5rem;
    align-items: start;
}

.panel {
    background: #fff;
    border: 2px solid rgba(65, 184, 131, 0.18);
    border-radius: 24px;
    padding: 1.5rem;
    box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
}

.controls h2 {
    margin-bottom: 0.5rem;
    color: var(--primary-color);
}

.helper {
    color: #64748b;
    line-height: 1.5;
    margin-bottom: 1.25rem;
}

.exercise-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
}

.exercise-btn,
.primary-btn,
.secondary-btn {
    border-radius: 14px;
    border: 2px solid var(--primary-color);
    cursor: pointer;
    transition: all 0.2s ease;
}

.exercise-btn {
    padding: 0.9rem 0.75rem;
    background: #fff;
    color: var(--secondary-color);
    text-transform: uppercase;
    font-weight: 600;
}

.exercise-btn.active,
.exercise-btn:hover,
.primary-btn:hover {
    background: var(--primary-color);
    color: #fff;
}

.action-row {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.25rem;
}

.primary-btn,
.secondary-btn {
    flex: 1;
    padding: 0.95rem 1rem;
    font-weight: 700;
}

.primary-btn {
    background: #fff;
    color: var(--primary-color);
}

.secondary-btn {
    background: transparent;
    color: #64748b;
    border-color: #cbd5e1;
}

.secondary-btn:hover {
    border-color: #94a3b8;
    color: #0f172a;
}

.status,
.error {
    margin-top: 1rem;
    font-size: 0.95rem;
}

.status {
    color: #475569;
}

.error {
    color: #dc2626;
}

.metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
}

.metric-card {
    background: #f8fafc;
    border-radius: 16px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.metric-card span {
    color: #64748b;
    font-size: 0.85rem;
    text-transform: uppercase;
}

.metric-card strong {
    color: #0f172a;
    font-size: 1.5rem;
}

.feedback {
    margin-top: 1rem;
    padding: 1rem 1.1rem;
    border-radius: 16px;
    background: rgba(65, 184, 131, 0.12);
    color: #166534;
    font-weight: 600;
    line-height: 1.5;
}

.feedback.bad {
    background: rgba(239, 68, 68, 0.12);
    color: #b91c1c;
}

.camera-panel {
    padding: 1rem;
}

.camera-stage {
    position: relative;
    overflow: hidden;
    border-radius: 22px;
    background: #0f172a;
    aspect-ratio: 4 / 3;
}

video,
.overlay {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
}

video {
    object-fit: cover;
    transform: scaleX(-1);
}

.overlay {
    pointer-events: none;
}

@media (max-width: 960px) {
    .realtime-page {
        grid-template-columns: 1fr;
    }
}
</style>
