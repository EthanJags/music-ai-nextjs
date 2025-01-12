"use client";

import { useState } from "react";

interface RecordingButtonProps {
  audioBlob: Blob | null;
  setAudioBlob: (blob: Blob | null) => void;
}

export default function RecordingButton({ audioBlob, setAudioBlob }: RecordingButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const startRecording = async () => {
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(audioStream);
      const audioChunks: BlobPart[] = [];

      recorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
        setAudioBlob(audioBlob);
        audioStream.getTracks().forEach(track => track.stop());
        setStream(null);
        setMediaRecorder(null);
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
    <div className="flex flex-col gap-4">
      <h2 className="text-xl">Record Audio</h2>
      {!isRecording ? (
        <button
          onClick={startRecording}
          className="rounded-full border border-solid transition-colors px-4 py-2 bg-foreground text-background hover:bg-[#383838]"
        >
          Start Recording
        </button>
      ) : (
        <button
          onClick={stopRecording}
          className="rounded-full border border-solid transition-colors px-4 py-2 bg-red-500 text-white hover:bg-red-600"
        >
          Stop Recording
        </button>
      )}
      {audioBlob && (
        <audio controls className="w-full">
          <source src={URL.createObjectURL(audioBlob)} type="audio/ogg" />
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
}
