"use client";

import RecordingButton from "./components/recording_button";
import SearchButton from "./components/SearchButton";
import { useState } from "react";
import Ranking from "./components/Ranking";

export default function Home() {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [searchMode, setSearchMode] = useState<("demo" | "own")[]>([]);
  const [rankedSounds, setRankedSounds] = useState<
    { filename: string; similarity: number }[]
  >([]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-200 dark:from-gray-900 dark:to-gray-800 text-gray-800 dark:text-gray-100">
      <div className="container max-w-[1400px] mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-4">Audio Similarity Search</h1>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            Find the closest audio match with your own voice.
          </p>
        </header>

        <main className="flex flex-col items-center space-y-6">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 transition-transform hover:scale-[1.01] w-full max-w-[600px]">
            <section>
              <h2 className="text-2xl font-semibold mb-4">Record Audio</h2>
              <RecordingButton audioBlob={audioBlob} setAudioBlob={setAudioBlob} />
            </section>

            <section>
              <h2 className="text-2xl font-semibold mb-4">Search</h2>
              <SearchButton
                audioBlob={audioBlob}
                searchMode={searchMode}
                setRankedSounds={setRankedSounds}
              />
            </section>
          </div>

          {/* {rankedSounds.length > 0 && ( */}
        
          {
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 transition-transform hover:scale-[1.01] w-full max-w-[600px]">
              <h2 className="text-2xl font-semibold mb-6">Similar Sounds</h2>
              <Ranking ranked_sounds={rankedSounds} />
            </div>
          }

          {/* )} */}
        </main>

        <footer className="mt-16 text-center text-sm text-gray-500 dark:text-gray-400">
          Made with ❤️ by <a href="https://ethanjagoda.com" className="hover:underline">Ethan Jagoda</a> & Aaditya Pore
        </footer>
      </div>
    </div>
  );
}