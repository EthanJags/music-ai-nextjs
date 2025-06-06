"use client";

import { useState } from "react";

interface ShowMoreProps {
  setRankedSounds: (rankedSounds: any) => void;
  startingIndex: number;
  setStartingIndex: (value: number | ((prev: number) => number)) => void;
  batchSize: number;
  ranking: any;
}

export default function ShowMore({ setRankedSounds, startingIndex, setStartingIndex, batchSize, ranking }: ShowMoreProps) {
    const [isLoading, setIsLoading] = useState(false);
    
    const showMore = async (startingIndex: number, batchSize: number) => {
        setIsLoading(true);
        try {
            const endIndex = startingIndex + batchSize;
            const filepaths = ranking.slice(startingIndex, endIndex).map((sound: { file_path: string }) => sound.file_path);
            const localurls3 = "http://localhost:3002/fetch_audio"
            const urls3 = "https://music-ai-79b29ebd624d.herokuapp.com/fetch_audio"
            const fetchString = `${urls3}?filepaths=${encodeURIComponent(filepaths.join(','))}`
            console.log("fetchString", fetchString)
            const audioResponse = await fetch(fetchString);
            const audioBlobs = await audioResponse.json();

            const rankedSoundsWithUrls = ranking
            .slice(startingIndex, endIndex)
            .map((sound:any, index:any) => ({
             ...sound,
              audioUrl: URL.createObjectURL(new Blob([audioBlobs[index]]))
              }));
              
            console.log("rankedSoundsWithUrls", rankedSoundsWithUrls)

            setStartingIndex((prev: number) => prev + batchSize);
            setRankedSounds((prev: any[]) => [...prev, ...rankedSoundsWithUrls]);

        } catch (error) {
            console.error('Error loading more results:', error);
        } finally {
            setIsLoading(false);
        }
    }

  return (
    <div className="flex justify-center mt-8">
      <button
        onClick={() => showMore(startingIndex, batchSize)}
        disabled={isLoading}
        className={`
          px-6 py-2 text-sm font-medium text-white 
          bg-indigo-600 rounded-md hover:bg-indigo-700 
          transition-colors
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
      >
        {isLoading ? (
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Loading...
          </div>
        ) : (
          'Show More'
        )}
      </button>
    </div>
  );
}