import React, { useState, useRef, useEffect } from 'react';
import DashboardLayout from '@/layouts/DashboardLayout';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '@/components/ui/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { textAPI } from '@/utils/api';
import {
  Mic,
  MicOff,
  Upload,
  FileText,
  AlertCircle,
  Play,
  Loader2,
  ArrowRight,
  Check,
  X,
  RefreshCw,
  Save,
  Download
} from 'lucide-react';

export default function TextProcessingPage() {
  const { toast } = useToast();
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [processingSteps, setProcessingSteps] = useState([]);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Processing steps based on backend process
  const processingStepsTemplate = [
    { id: 1, name: 'Parsing input', description: 'Analyzing input text structure' },
    { id: 2, name: 'Semantic analysis', description: 'Extracting meaning and context' },
    { id: 3, name: 'Knowledge retrieval', description: 'Retrieving relevant information' },
    { id: 4, name: 'Reasoning', description: 'Applying reasoning chains to input' },
    { id: 5, name: 'Response generation', description: 'Generating comprehensive response' }
  ];

  // Start recording function
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioFile(audioBlob);
        setUploadedFileName('Recorded Audio');

        try {
          // Send the audio to the API for transcription
          setIsProcessing(true);
          toast({
            title: 'Transcribing Audio',
            description: 'Processing your audio for transcription...',
          });
          
          const result = await textAPI.transcribeAudio(audioBlob);
          setText(result.text);
          
          toast({
            title: 'Audio Transcribed',
            description: 'Your audio has been successfully transcribed',
          });
        } catch (error) {
          console.error('Audio transcription error:', error);
          toast({
            variant: 'destructive',
            title: 'Transcription Failed',
            description: 'Failed to transcribe audio. Please try again.',
          });
          
          // Fallback for development or when API fails
          setText("This is a simulated transcription of recorded audio. In a real application, this would be the text returned by the transcription API.");
        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      toast({
        variant: 'destructive',
        title: 'Microphone Access Failed',
        description: 'Please ensure you have given permission to use the microphone.',
      });
    }
  };

  // Stop recording function
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
    }
  };

  // Handle file upload
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFileName(file.name);

      // For audio files, set up for transcription
      if (file.type.startsWith('audio/')) {
        setAudioFile(file);
        try {
          setIsProcessing(true);
          toast({
            title: 'Transcribing Audio',
            description: 'Processing your audio file for transcription...',
          });
          
          const result = await textAPI.transcribeAudio(file);
          setText(result.text);
          
          toast({
            title: 'Audio Transcribed',
            description: 'Your audio has been successfully transcribed',
          });
        } catch (error) {
          console.error('Audio transcription error:', error);
          toast({
            variant: 'destructive',
            title: 'Transcription Failed',
            description: 'Failed to transcribe audio. Please try again.',
          });
          
          // Fallback for development or when API fails
          setText("This is a simulated transcription of the uploaded audio file. In a real application, this would be the text returned by the transcription API.");
        } finally {
          setIsProcessing(false);
        }
      } 
      // For text files, read their content
      else if (file.type === 'text/plain' || file.type === 'application/pdf' || file.type === 'application/msword') {
        const reader = new FileReader();
        reader.onload = (e) => {
          setText(e.target.result);
        };
        reader.readAsText(file);
      } else {
        toast({
          variant: 'destructive',
          title: 'Unsupported File Type',
          description: 'Please upload an audio or text file.',
        });
      }
    }
  };

  // Processing function
  const handleProcessText = async () => {
    if (!text.trim()) {
      toast({
        variant: 'destructive',
        title: 'Empty Input',
        description: 'Please enter some text or upload audio to process.',
      });
      return;
    }

    setIsProcessing(true);
    setProcessingStage(0);
    setProcessingSteps(processingStepsTemplate);
    setResults(null);
    setError(null);

    try {
      // Start processing animation
      let stageInterval = setInterval(() => {
        setProcessingStage(stage => {
          if (stage < processingStepsTemplate.length) {
            return stage + 1;
          }
          clearInterval(stageInterval);
          return stage;
        });
      }, 800);

      // Make the actual API call
      const response = await textAPI.processText({ text });
      
      // Clear interval if response comes back quickly
      clearInterval(stageInterval);
      setProcessingStage(processingStepsTemplate.length);
      
      setResults(response);
    } catch (err) {
      console.error('Processing error:', err);
      setError('An error occurred while processing your text. Please try again.');
      
      // Fallback for development or when API fails
      setResults({
        result: "Based on the analysis, this text discusses artificial intelligence applications in healthcare, focusing on diagnostic tools and patient care optimization.",
        reasoning: [
          { id: 1, thought: "Identifying key topics in the text", explanation: "Scanning for main subjects, technical terms, and contextual clues." },
          { id: 2, thought: "Connecting concepts to knowledge base", explanation: "Relating identified topics to known frameworks in the domain." },
          { id: 3, thought: "Evaluating significance of mentioned technologies", explanation: "Assessing the relevance and impact of mentioned tools and methods." },
          { id: 4, thought: "Contextualizing within broader field", explanation: "Placing the discussed items within the larger industry landscape." },
          { id: 5, thought: "Formulating comprehensive summary", explanation: "Creating a cohesive overview that captures key points and implications." }
        ]
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // Reset all states
  const handleReset = () => {
    setText('');
    setAudioFile(null);
    setResults(null);
    setError(null);
    setUploadedFileName('');
    setProcessingStage(0);
    setProcessingSteps([]);
  };

  // Save results as text file
  const handleSaveResults = async () => {
    if (!results) return;
    
    try {
      // Use the API to save the processed text
      await textAPI.saveProcessed({
        text: text,
        result: results.result,
        reasoning: results.reasoning
      });
      
      toast({
        title: 'Results Saved',
        description: 'The processing results have been saved to your account.',
      });
    } catch (error) {
      console.error('Error saving results:', error);
      toast({
        variant: 'destructive',
        title: 'Save Failed',
        description: 'Failed to save results. Please try again.',
      });
      
      // Fallback if API fails - save as text file
      const content = `
Results: ${results.result}

Reasoning:
${results.reasoning.map(step => `${step.id}. ${step.thought}: ${step.explanation}`).join('\n')}
      `;
      
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'text-processing-results.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: 'Results Saved Locally',
        description: 'The processing results have been saved as a text file.',
      });
    }
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isRecording]);

  return (
    <DashboardLayout 
      title="Text Processing"
      description="Process text with AI and get detailed analysis results"
    >
      <div className="space-y-6">
        {/* Input Section */}
        <Card>
          <CardHeader>
            <CardTitle>Text Input</CardTitle>
            <CardDescription>
              Enter text directly, record audio, or upload a file for processing
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="text" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="text">
                  <FileText className="h-4 w-4 mr-2" />
                  Text Input
                </TabsTrigger>
                <TabsTrigger value="audio">
                  <Mic className="h-4 w-4 mr-2" />
                  Audio Input
                </TabsTrigger>
                <TabsTrigger value="file">
                  <Upload className="h-4 w-4 mr-2" />
                  File Upload
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="text" className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="text-input">Enter your text:</Label>
                  <Textarea
                    id="text-input"
                    placeholder="Type or paste your text here..."
                    className="min-h-[200px]"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                </div>
              </TabsContent>
              
              <TabsContent value="audio" className="space-y-6 mt-4">
                <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg text-center">
                  {!isRecording && !audioFile && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center"
                    >
                      <Mic className="h-12 w-12 text-slate-400 mb-4" />
                      <p className="text-slate-500 dark:text-slate-400 mb-4">
                        Record audio for transcription using Whisper
                      </p>
                      <Button onClick={startRecording}>
                        Start Recording
                      </Button>
                    </motion.div>
                  )}
                  
                  {isRecording && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center"
                    >
                      <motion.div
                        animate={{
                          scale: [1, 1.2, 1],
                          opacity: [1, 0.8, 1],
                        }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                          repeatType: "loop"
                        }}
                        className="relative"
                      >
                        <div className="absolute -inset-1 rounded-full bg-red-500/20 animate-pulse" />
                        <Mic className="h-12 w-12 text-red-500" />
                      </motion.div>
                      <p className="text-slate-500 dark:text-slate-400 mt-4 mb-4">
                        Recording in progress...
                      </p>
                      <Button variant="destructive" onClick={stopRecording}>
                        Stop Recording
                      </Button>
                    </motion.div>
                  )}
                  
                  {!isRecording && audioFile && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center"
                    >
                      <div className="flex items-center justify-center w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full mb-4">
                        <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
                      </div>
                      <p className="text-slate-500 dark:text-slate-400 mb-1">
                        {uploadedFileName || 'Audio recorded'}
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
                        Transcription complete
                      </p>
                      <div className="flex gap-2">
                        <Button variant="outline" onClick={() => {
                          setAudioFile(null);
                          setUploadedFileName('');
                        }}>
                          Record Again
                        </Button>
                      </div>
                    </motion.div>
                  )}
                </div>
                
                {audioFile && (
                  <div className="space-y-2">
                    <Label htmlFor="transcribed-text">Transcribed Text:</Label>
                    <Textarea
                      id="transcribed-text"
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      className="min-h-[150px]"
                    />
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="file" className="space-y-6 mt-4">
                <div 
                  className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-lg text-center cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".txt,.pdf,.doc,.docx,.mp3,.wav,.ogg"
                    onChange={handleFileUpload}
                  />
                  
                  {!uploadedFileName ? (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center"
                    >
                      <Upload className="h-12 w-12 text-slate-400 mb-4" />
                      <p className="text-slate-500 dark:text-slate-400 mb-2">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
                        Supports text files (.txt, .pdf, .doc) and audio files (.mp3, .wav, .ogg)
                      </p>
                      <Button variant="outline">
                        Select File
                      </Button>
                    </motion.div>
                  ) : (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex flex-col items-center"
                    >
                      <div className="flex items-center justify-center w-12 h-12 bg-sky-100 dark:bg-sky-900/30 rounded-full mb-4">
                        <Check className="h-6 w-6 text-sky-600 dark:text-sky-400" />
                      </div>
                      <p className="text-slate-500 dark:text-slate-400 mb-1">
                        {uploadedFileName}
                      </p>
                      <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
                        File uploaded successfully
                      </p>
                      <Button variant="outline" onClick={(e) => {
                        e.stopPropagation();
                        setUploadedFileName('');
                        setAudioFile(null);
                      }}>
                        Change File
                      </Button>
                    </motion.div>
                  )}
                </div>
                
                {uploadedFileName && (
                  <div className="space-y-2">
                    <Label htmlFor="file-text">File Content:</Label>
                    <Textarea
                      id="file-text"
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      className="min-h-[150px]"
                    />
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={handleReset} disabled={isProcessing}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Reset
            </Button>
            <Button 
              onClick={handleProcessText} 
              disabled={isProcessing || !text.trim()}
              className="flex items-center gap-2"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Process Text
                </>
              )}
            </Button>
          </CardFooter>
        </Card>

        {/* Processing Status */}
        <AnimatePresence>
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Processing Status</CardTitle>
                  <CardDescription>Current progress of your text analysis</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Progress value={processingStage * 100 / processingSteps.length} className="h-2" />
                  
                  <div className="space-y-2">
                    {processingSteps.map((step, index) => (
                      <div 
                        key={step.id}
                        className={`flex items-start p-2 rounded-md transition-colors ${
                          index < processingStage 
                            ? 'bg-green-50 dark:bg-green-900/10' 
                            : index === processingStage - 1 
                              ? 'bg-sky-50 dark:bg-sky-900/10' 
                              : 'bg-slate-50 dark:bg-slate-800/30'
                        }`}
                      >
                        <div className="mr-3 mt-0.5">
                          {index < processingStage ? (
                            <motion.div
                              initial={{ scale: 0.5 }}
                              animate={{ scale: 1 }}
                              className="h-5 w-5 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center"
                            >
                              <Check className="h-3 w-3 text-green-600 dark:text-green-400" />
                            </motion.div>
                          ) : index === processingStage - 1 ? (
                            <motion.div
                              animate={{ 
                                rotate: 360,
                                transition: { duration: 1, repeat: Infinity, ease: "linear" } 
                              }}
                              className="h-5 w-5 text-sky-600 dark:text-sky-400"
                            >
                              <Loader2 className="h-5 w-5" />
                            </motion.div>
                          ) : (
                            <div className="h-5 w-5 rounded-full border-2 border-slate-300 dark:border-slate-600" />
                          )}
                        </div>
                        <div>
                          <p className={`text-sm font-medium ${
                            index < processingStage 
                              ? 'text-green-700 dark:text-green-400' 
                              : index === processingStage - 1 
                                ? 'text-sky-700 dark:text-sky-400' 
                                : 'text-slate-600 dark:text-slate-400'
                          }`}>
                            {step.name}
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-500">
                            {step.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {results && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: 0.2 }}
              className="space-y-6"
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Processing Results</span>
                    <Button variant="outline" size="sm" onClick={handleSaveResults}>
                      <Save className="h-4 w-4 mr-2" />
                      Save Results
                    </Button>
                  </CardTitle>
                  <CardDescription>AI analysis of your processed text</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-md border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-2">Summary</h3>
                    <p className="text-slate-700 dark:text-slate-300">{results.result}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-3">Chain of Thought Reasoning</h3>
                    <ScrollArea className="h-64 rounded-md border border-slate-200 dark:border-slate-700 p-4">
                      <div className="space-y-4">
                        {results.reasoning.map((step, index) => (
                          <motion.div 
                            key={step.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="relative pl-8 border-l-2 border-slate-200 dark:border-slate-700"
                          >
                            <div className="absolute -left-2 top-0 flex items-center justify-center w-4 h-4 rounded-full bg-sky-500 text-white">
                              <span className="text-xs">{step.id}</span>
                            </div>
                            <h4 className="text-sm font-medium text-slate-900 dark:text-slate-100">{step.thought}</h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{step.explanation}</p>
                          </motion.div>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Error State */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              <Card className="border-red-200 dark:border-red-900">
                <CardHeader className="text-red-600 dark:text-red-400">
                  <CardTitle className="flex items-center">
                    <AlertCircle className="h-5 w-5 mr-2" />
                    Processing Error
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-slate-700 dark:text-slate-300">{error}</p>
                </CardContent>
                <CardFooter>
                  <Button variant="outline" onClick={handleReset}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Start Over
                  </Button>
                </CardFooter>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DashboardLayout>
  );
} 