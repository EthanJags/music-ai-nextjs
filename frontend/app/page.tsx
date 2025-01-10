"use client";

import RecordingButton from "./components/recording_button";
// import FileUploader from "./components/file_uploader";
import SearchButton from "./components/SearchButton";
import { useState } from "react";
// import SearchModeSelector from "./components/SearchModeSelector";
import Ranking from "./components/Ranking";

export default function Home() {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [searchMode, setSearchMode] = useState<("demo" | "own")[]>([]);
  const [rankedSounds, setRankedSounds] = useState<{
    filename: string;
    similarity: number;
  }[]>([]);

  return (
    <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <main className="flex flex-col gap-8 row-start-2 items-center">
        <h1 className="text-2xl font-bold mb-8">Audio Processing Tool</h1>

        <div className="flex flex-col gap-8 w-full max-w-md">
          {/* File Upload Section */}
          {/* <FileUploader /> */}

          {/* Audio Recording Section */}
          <RecordingButton audioBlob={audioBlob} setAudioBlob={setAudioBlob} />

          {/* Search Mode Selection */}
          {/* <SearchModeSelector searchMode={searchMode} setSearchMode={setSearchMode} /> */}

          {/* Search Section */}
          <SearchButton audioBlob={audioBlob} searchMode={searchMode} setRankedSounds={setRankedSounds} />

          {/* Results Section */}
          <Ranking ranked_sounds={rankedSounds} />
        </div>
      </main>

      <footer className="row-start-3 text-sm text-gray-500">
        Click Stop to end recording
      </footer>
      
    </div>
  );
}
