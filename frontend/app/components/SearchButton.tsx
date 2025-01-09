"use client";

import { useState } from "react";

interface SearchButtonProps {
  audioBlob: Blob | null;
  searchMode: 'demo' | 'own';
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
      const response = await fetch(`http://localhost:3002/search`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error('Search failed');
      }
      console.log('Search response:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        url: response.url
      });
      
      const { ranked_sounds } = await response.json();
      console.log("ranked_sounds: ", ranked_sounds);
      setRankedSounds(ranked_sounds);
      
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
