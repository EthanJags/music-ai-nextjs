"use client";

import { useState } from "react";

interface SearchButtonProps {
  audioBlob: Blob | null;
}

export default function SearchButton({ audioBlob }: SearchButtonProps) {
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
      formData.append('audio', audioBlob);

      const response = await fetch(`${process.env.BACKEND_URL}/api/search`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const results = await response.json();
      
      setSearchStatus({
        type: "success",
        message: "Search completed successfully!"
      });

      // Handle search results here
      console.log(results);

    } catch (error) {
      console.error('Error searching:', error);
      setSearchStatus({
        type: "error",
        message: "Failed to perform search. Please try again."
      });
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
