import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Mic, Square, Play, Trash, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

const VoiceRecorder = ({ 
  onSave, 
  onClear, 
  className, 
  maxDuration = 60 
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioUrl, setAudioUrl] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioRef = useRef(null);
  const timerRef = useRef(null);
  
  // Clean up resources when unmounting
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      clearInterval(timerRef.current);
    };
  }, [audioUrl]);
  
  // Start recording function
  const startRecording = async () => {
    try {
      // Reset existing recording if any
      if (audioBlob) {
        setAudioBlob(null);
        setAudioUrl(null);
      }
      
      audioChunksRef.current = [];
      setRecordingTime(0);
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setAudioBlob(audioBlob);
        setAudioUrl(audioUrl);
        
        // Stop all tracks in the stream
        stream.getTracks().forEach(track => track.stop());
      };
      
      // Start recording and timer
      mediaRecorderRef.current.start();
      setIsRecording(true);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prevTime => {
          if (prevTime >= maxDuration) {
            stopRecording();
            return maxDuration;
          }
          return prevTime + 1;
        });
      }, 1000);
    } catch (error) {
      console.error('Error starting recording:', error);
    }
  };
  
  // Stop recording function
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };
  
  // Play recording function
  const playRecording = () => {
    if (audioRef.current && audioUrl) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };
  
  // Handle audio end event
  const handleAudioEnded = () => {
    setIsPlaying(false);
  };
  
  // Clear recording function
  const clearRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    
    if (onClear) {
      onClear();
    }
  };
  
  // Handle save recording
  const handleSave = () => {
    if (audioBlob && onSave) {
      onSave(audioBlob);
    }
  };
  
  // Format recording time as MM:SS
  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className={cn('p-4 border rounded-lg bg-white dark:bg-slate-800 w-full', className)}>
      <h3 className="text-sm font-medium mb-2">Voice Feedback</h3>
      
      {/* Recording progress */}
      <div className="flex items-center gap-2 mb-3">
        <Progress 
          value={(recordingTime / maxDuration) * 100} 
          className="h-2 flex-1"
        />
        <span className="text-xs text-slate-500 dark:text-slate-400 min-w-[40px] text-right">
          {formatTime(recordingTime)}
        </span>
      </div>
      
      {/* Controls */}
      <div className="flex gap-2">
        {isRecording ? (
          <Button 
            variant="destructive" 
            size="sm"
            onClick={stopRecording}
            className="flex-1"
          >
            <Square className="h-4 w-4 mr-2" />
            Stop Recording
          </Button>
        ) : (
          <Button 
            variant={audioBlob ? "outline" : "default"} 
            size="sm"
            onClick={startRecording}
            className="flex-1"
            disabled={isPlaying}
          >
            <Mic className="h-4 w-4 mr-2" />
            {audioBlob ? "Record Again" : "Start Recording"}
          </Button>
        )}
        
        {audioBlob && !isRecording && (
          <>
            <Button 
              variant="outline" 
              size="sm"
              onClick={playRecording}
              disabled={isRecording}
            >
              <Play className="h-4 w-4" />
              <span className="sr-only">{isPlaying ? "Pause" : "Play"}</span>
            </Button>
            
            <Button 
              variant="outline" 
              size="sm"
              onClick={clearRecording}
              disabled={isRecording}
            >
              <Trash className="h-4 w-4" />
              <span className="sr-only">Delete</span>
            </Button>
            
            <Button 
              variant="default" 
              size="sm"
              onClick={handleSave}
              disabled={isRecording}
            >
              <Save className="h-4 w-4 mr-2" />
              Save
            </Button>
          </>
        )}
      </div>
      
      {/* Sound visualization animation during recording */}
      {isRecording && (
        <div className="flex items-center justify-center gap-1 h-6 mt-3">
          {[...Array(5)].map((_, i) => (
            <motion.div
              key={i}
              className="w-1 bg-sky-500 rounded-full"
              animate={{
                height: [8, 16, 24, 16, 8],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: i * 0.1,
              }}
            />
          ))}
        </div>
      )}
      
      {/* Hidden audio element for playback */}
      <audio 
        ref={audioRef} 
        src={audioUrl} 
        onEnded={handleAudioEnded} 
        className="hidden"
      />
    </div>
  );
};

export { VoiceRecorder }; 