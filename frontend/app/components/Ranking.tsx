import { FC } from 'react';
import { useState } from 'react';

interface RankedSound {
  filename: string;
  similarity: number;
  audioUrl?: string;
}

interface RankingProps {
  ranked_sounds?: RankedSound[];
}

const RankedSoundItem = ({ sound, index }: { sound: RankedSound; index: number }) => {
  const [isPlaying, setIsPlaying] = useState(false);

  return (
    <div 
      key={sound.filename}
      className="flex flex-col gap-2 p-3 bg-gray-50 rounded-lg cursor-pointer"
      onClick={() => setIsPlaying(!isPlaying)}
    >
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="text-gray-500">{index + 1}.</span>
          <span className="font-medium text-gray-500">{sound.filename}</span>
        </div>
        <span className="text-sm text-gray-600">
          {(sound.similarity * 100).toFixed(1)}% match
        </span>
      </div>
      {isPlaying && (
        <audio controls controlsList="nodownload noplaybackrate" className="w-full">
          <source src={sound.audioUrl} type="audio/ogg" />
          Your browser does not support the audio element.
        </audio>
      )}
      <a href={sound.audioUrl} download={sound.filename} className="text-blue-500 hover:text-blue-700">
        Download sound
      </a>
    </div>
  );
};



const Ranking: FC<RankingProps> = ({ ranked_sounds = [] }) => {
  if (!ranked_sounds.length) return null;

  return (
    <div className="w-full">
      <h2 className="text-lg font-semibold mb-4">Similar Sounds</h2>
      <div className="space-y-2">
        {ranked_sounds.map((sound, index) => (
          <RankedSoundItem 
            key={sound.filename}
            sound={sound} 
            index={index}
          />
        ))}
      </div>
    </div>
  );
};

export default Ranking;
