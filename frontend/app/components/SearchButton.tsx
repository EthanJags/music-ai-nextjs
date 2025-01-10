"use client";

import { useState } from "react";
import JSZip from 'jszip';

interface SearchButtonProps {
  audioBlob: Blob | null;
  searchMode: ("demo" | "own")[];
  setRankedSounds: (sounds: {
    filename: string;
    similarity: number;
  }[]) => void;
}

export default function SearchButton({ audioBlob, searchMode, setRankedSounds }: SearchButtonProps) {
  const [isSearching, setIsSearching] = useState(false);
  const [searchStatus, setSearchStatus] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const handleSearch = async () => {
    if (!audioBlob) return;
    setIsSearching(true);
    setSearchStatus(null);

    try {
      const formData = new FormData();
      const file = new File([audioBlob], 'user_input.adg.ogg', { 
        type: 'audio/ogg' 
      });
      formData.append('audio_file', file);
      
      const response = await fetch(`https://music-ai-79b29ebd624d.herokuapp.com/search`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      // Get rankings data from header
      const rankingsHeader = response.headers.get('X-Rankings-Data');
      if (rankingsHeader) {
        // Decode base64 rankings data
        const rankingsJson = atob(rankingsHeader);
        const rankings = JSON.parse(rankingsJson);
        setRankedSounds(rankings.ranked_sounds);
      }

      // Handle zip file
      const blob = await response.blob();
      const zip = await JSZip.loadAsync(blob);
      
      // Extract audio files from zip
      const audioFiles = new Map();
      for (const [filename, file] of Object.entries(zip.files)) {
        if (!filename.startsWith('__MACOSX')) { // Skip macOS metadata
          const audioBlob = await file.async('blob'); 
          console.log("filename from extractting zip", filename);
          audioFiles.set(filename, URL.createObjectURL(audioBlob));
        }
      }

      // Update ranked sounds with audio URLs
      if (rankingsHeader) {
        const rankingsJson = atob(rankingsHeader);
        const rankings = JSON.parse(rankingsJson);
        
        // Add audio URLs to ranked sounds
        const rankedSoundsWithUrls = rankings.ranked_sounds.map((sound: { filename: string; similarity: number; file_id: string }) => ({
          ...sound,
          audioUrl: audioFiles.get(sound.filename)
        }));
        
        setRankedSounds(rankedSoundsWithUrls);
        console.log("rankedSoundsWithUrls", rankedSoundsWithUrls);
      }
      
      setSearchStatus({
        type: "success",
        message: "Search completed successfully!"
      });

    } catch (error) {
      console.error('Error searching:', error);
      setSearchStatus({
        type: "error",
        message: "Failed to perform search. Please try again."
      });
      setRankedSounds([]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={handleSearch}
        disabled={!audioBlob || isSearching}
        className="rounded-full border border-solid transition-colors px-4 py-2 bg-foreground text-background hover:bg-[#383838] disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSearching ? 'Searching...' : 'Search with Audio'}
      </button>

      {searchStatus && (
        <div className={`p-3 rounded ${
          searchStatus.type === "success" 
            ? "bg-green-100 text-green-700 border border-green-200" 
            : "bg-red-100 text-red-700 border border-red-200"
        }`}>
          {searchStatus.message}
        </div>
      )}
    </div>
  );
}