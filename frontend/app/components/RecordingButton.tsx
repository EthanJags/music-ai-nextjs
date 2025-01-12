"use client";

import { useState, useEffect } from "react";
import { Mic, Square, Play, Pause } from "lucide-react";

interface RecordingButtonProps {
  audioBlob: Blob | null;
  setAudioBlob: (blob: Blob | null) => void;
}

export default function RecordingButton({ audioBlob, setAudioBlob }: RecordingButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(audioStream);
      const audioChunks: BlobPart[] = [];

      recorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/ogg" });
        setAudioBlob(audioBlob);
        audioStream.getTracks().forEach(track => track.stop());
        setStream(null);
        setMediaRecorder(null);
        setRecordingTime(0);
      };

      setIsRecording(true);
      setStream(audioStream);
      setMediaRecorder(recorder);
      recorder.start();
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="relative flex items-center gap-4">
          {isRecording ? (
            <button
              onClick={stopRecording}
              className="relative group"
            >
              <div className="absolute inset-0 bg-red-500 rounded-xl blur-lg opacity-20 group-hover:opacity-30 transition-opacity" />
              <div className="relative flex items-center gap-2 px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-all duration-300 font-medium">
                <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
                <Square className="w-4 h-4" />
                <span>Stop Recording</span>
                <span className="ml-2 text-red-100">{formatTime(recordingTime)}</span>
              </div>
            </button>
          ) : (
            <button
              onClick={startRecording}
              className={`
                relative group overflow-hidden
                px-6 py-3 rounded-xl
                bg-gradient-to-r from-indigo-500 to-purple-500
                dark:from-indigo-600 dark:to-purple-600
                text-white font-medium
                transition-all duration-300
                hover:shadow-lg hover:shadow-indigo-500/25
                dark:hover:shadow-indigo-600/25
              `}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-700 dark:to-purple-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative flex items-center gap-2">
                <Mic className="w-4 h-4" />
                <span>Start Recording</span>
              </div>
            </button>
          )}
        </div>
      </div>

      {audioBlob && (
        <div className="rounded-xl bg-gray-50/80 dark:bg-gray-900/50 backdrop-blur-sm border border-gray-200 dark:border-gray-700 p-4 transition-all duration-300 hover:shadow-md">
          <audio
            controls
            className="w-full"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          >
            <source src={URL.createObjectURL(audioBlob)} type="audio/ogg" />
            Your browser does not support the audio element.
          </audio>
        </div>
      )}
    </div>
  );
}