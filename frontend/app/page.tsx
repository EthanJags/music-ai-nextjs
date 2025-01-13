"use client";

import RecordingButton from "./components/RecordingButton";
import SearchButton from "./components/SearchButton";
import { useState, useEffect } from "react";
import Ranking from "./components/Ranking";
import { Waves } from "lucide-react";

export default function Home() {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [searchMode, setSearchMode] = useState([]);
  const [rankedSounds, setRankedSounds] = useState<{
    filename: string;
    similarity: number;
    audioUrl?: string;
  }[]>([]);

  const [currentPage, setCurrentPage] = useState(1);
  const resultsPerPage = 10;

  const indexOfLastResult = currentPage * resultsPerPage;
  const indexOfFirstResult = indexOfLastResult - resultsPerPage;
  const currentResults = rankedSounds?.slice(indexOfFirstResult, indexOfLastResult);

  const totalPages = Math.ceil((rankedSounds?.length || 0) / resultsPerPage);

  const paginate = (pageNumber: number) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-indigo-950 dark:to-purple-950 text-gray-800 dark:text-gray-100">
      <div className="absolute inset-0 bg-grid-pattern opacity-5 pointer-events-none" />
      
      <div className="relative container max-w-6xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        <header className="text-center mb-16 space-y-4">
          <div className="flex items-center justify-center mb-6">
            <Waves className="w-12 h-12 text-indigo-600 dark:text-indigo-400 animate-pulse" />
          </div>
          <h1 className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400">
            Sound Similarity Search
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Discover perfect audio matches with the power of your voice. Advanced AI-powered similarity detection at your fingertips.
          </p>
          <script data-name="BMC-Widget" data-cfasync="false" src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js" data-id="aadityacobra" data-description="Support me on Buy me a coffee!" data-message="Thanks for visiting! If you enjoyed our work, buy us a coffee!" data-color="#BD5FFF" data-position="Right" data-x_margin="18" data-y_margin="18"></script>
        </header>

        <main className="flex flex-col items-center space-y-8">
          <div className="text-center bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg rounded-3xl shadow-2xl p-8 transition-all duration-300 hover:shadow-indigo-200 dark:hover:shadow-indigo-900 w-full max-w-2xl border border-gray-100 dark:border-gray-700">
            <section className="space-y-8">
              <div className="text-center">
                <h2 className="text-2xl font-semibold mb-4 flex items-center gap-2">
                  Record Audio
                </h2>
                <RecordingButton audioBlob={audioBlob} setAudioBlob={setAudioBlob} />
              </div>

              <SearchButton
                  audioBlob={audioBlob}
                  searchMode={searchMode}
                  setRankedSounds={setRankedSounds}
                />
            </section>
          </div>

          {<div className={`bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg rounded-3xl shadow-2xl p-8 transition-all duration-300 w-full max-w-2xl border border-gray-100 dark:border-gray-700 ${rankedSounds.length > 0 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
              <div className="w-1 h-6 bg-pink-600 rounded-full" />
              Similar Sounds
            </h2>
            <Ranking ranked_sounds={currentResults} />
          </div>}

          {rankedSounds && rankedSounds.length > resultsPerPage && (
            <div className="flex justify-center gap-2 mt-8 mb-8">
              <button
                onClick={() => paginate(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              
              {[...Array(totalPages)].map((_, index) => (
                <button
                  key={index + 1}
                  onClick={() => paginate(index + 1)}
                  className={`px-4 py-2 text-sm font-medium rounded-md ${
                    currentPage === index + 1
                      ? 'bg-blue-500 text-white'
                      : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {index + 1}
                </button>
              ))}

              <button
                onClick={() => paginate(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </main>

        <footer className="mt-16 text-center space-y-4">
          <div className="inline-flex items-center space-x-1 text-sm text-gray-500 dark:text-gray-400 bg-white/50 dark:bg-gray-800/50 rounded-full px-4 py-2 backdrop-blur-sm">
            <span>Made with</span>
            <span className="text-red-500 animate-pulse">❤️</span>
            <span>by</span>
            <a href="https://ethanjagoda.com" className="text-indigo-600 dark:text-indigo-400 hover:underline font-medium">
              Ethan Jagoda
            </a>
            <span>&</span>
            <a href= "https://aadityapore.webflow.io/" className="text-purple-600 dark:text-purple-400 hover:underline font-medium">
              Aaditya Pore
            </a>
          </div>

        </footer>
      </div>
    </div>
  );
}