import React, { useState, useEffect, useRef } from 'react';
import DashboardLayout from '@/components/layouts/DashboardLayout';
import { motion, AnimatePresence } from 'framer-motion';
import { useToast } from '@/components/ui/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogClose } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { arAPI } from '@/utils/api';
import {
  Play,
  Pause,
  SkipForward,
  VolumeX,
  Volume2,
  Headphones,
  Layers,
  Cube,
  Eye,
  Monitor,
  Smartphone,
  Wifi,
  RefreshCw,
  Info,
  Plus,
  ExternalLink,
  MessageSquare,
  X,
  Download,
  Settings,
  Share2,
  Star,
  Users,
  Zap,
} from 'lucide-react';

// Fallback AR scenes for when API fails
const fallbackScenes = [
  {
    id: 1,
    title: 'Medical Anatomy Explorer',
    description: 'Interactive 3D model of human anatomy with educational annotations',
    thumbnail: '/ar-thumbnails/anatomy.jpg',
    category: 'Education',
    rating: 4.8,
    usageCount: 2456,
    createdAt: '2023-10-15',
    tags: ['medical', 'education', 'anatomy'],
    status: 'featured'
  },
  // ... other fallback scenes
];

export default function ARExperiencePage() {
  const { toast } = useToast();
  const [scenes, setScenes] = useState([]);
  const [selectedScene, setSelectedScene] = useState(null);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isARActive, setIsARActive] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volume, setVolume] = useState(80);
  const [isMuted, setIsMuted] = useState(false);
  const [speechText, setSpeechText] = useState('');
  const [isSceneLoading, setIsSceneLoading] = useState(false);
  const [isCompatible, setIsCompatible] = useState(true);
  const [deviceType, setDeviceType] = useState('desktop');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const canvasRef = useRef(null);
  const speechSynthesisRef = useRef(null);

  // Fetch AR scenes from the API
  useEffect(() => {
    const fetchScenes = async () => {
      try {
        setIsLoading(true);
        const fetchedScenes = await arAPI.getScenes();
        setScenes(fetchedScenes);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch AR scenes:', err);
        setError('Failed to load AR scenes. Please try again.');
        setScenes(fallbackScenes);
      } finally {
        setIsLoading(false);
      }
    };

    fetchScenes();
  }, []);

  // Filtered scenes based on search query and filter
  const filteredScenes = scenes.filter(scene => {
    const matchesSearch = scene.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          scene.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          scene.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    if (filter === 'all') return matchesSearch;
    if (filter === 'featured') return matchesSearch && scene.status === 'featured';
    if (filter === 'recent') return matchesSearch && scene.status === 'recent';
    
    return matchesSearch && scene.category.toLowerCase() === filter.toLowerCase();
  });

  // Check device type and AR compatibility
  useEffect(() => {
    // Detect if mobile
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );
    setDeviceType(isMobile ? 'mobile' : 'desktop');

    // Check WebXR compatibility
    if (navigator.xr) {
      navigator.xr.isSessionSupported('immersive-ar')
        .then(supported => {
          setIsCompatible(supported);
        })
        .catch(() => {
          setIsCompatible(false);
        });
    } else {
      setIsCompatible(false);
    }
  }, []);

  // Initialize speech synthesis
  useEffect(() => {
    if ('speechSynthesis' in window) {
      speechSynthesisRef.current = window.speechSynthesis;
    }
    
    return () => {
      if (speechSynthesisRef.current) {
        speechSynthesisRef.current.cancel();
      }
    };
  }, []);

  // Handle scene selection
  const handleSelectScene = async (scene) => {
    setSelectedScene(scene);
    setIsSceneLoading(true);
    
    try {
      // Get detailed scene information
      const detailedScene = await arAPI.getSceneById(scene.id);
      setSelectedScene(detailedScene);
      setSpeechText(`Welcome to ${detailedScene.title}. This AR experience lets you explore ${detailedScene.description}.`);
    } catch (err) {
      console.error('Failed to fetch scene details:', err);
      toast({
        variant: "destructive",
        title: "Failed to Load Scene",
        description: "Could not load scene details. Please try again."
      });
      // Use the basic scene info we already have
      setSpeechText(`Welcome to ${scene.title}. This AR experience lets you explore ${scene.description}.`);
    } finally {
      setIsSceneLoading(false);
    }
  };

  // Handle AR launch
  const handleLaunchAR = async () => {
    if (!isCompatible) {
      toast({
        variant: "destructive",
        title: "AR Not Supported",
        description: "Your device doesn't support WebXR or AR features."
      });
      return;
    }
    
    if (!selectedScene) {
      toast({
        variant: "destructive",
        title: "No Scene Selected",
        description: "Please select an AR scene first."
      });
      return;
    }
    
    setIsARActive(true);
    
    try {
      // Launch the AR scene
      await arAPI.launchScene(selectedScene.id, {
        deviceType,
        volume: isMuted ? 0 : volume,
        enableAudio: !isMuted
      });
      
      toast({
        title: "AR Experience Launched",
        description: `${selectedScene.title} is now running in AR mode.`
      });
    } catch (err) {
      console.error('Failed to launch AR scene:', err);
      toast({
        variant: "destructive",
        title: "Launch Failed",
        description: "Could not launch the AR experience. Please try again."
      });
      setIsARActive(false);
    }
  };
  
  // Handle text-to-speech
  const handleSpeak = () => {
    if (!speechText || !speechSynthesisRef.current) return;
    
    // Cancel any ongoing speech
    if (speechSynthesisRef.current.speaking) {
      speechSynthesisRef.current.cancel();
      setIsSpeaking(false);
      return;
    }
    
    const utterance = new SpeechSynthesisUtterance(speechText);
    utterance.volume = isMuted ? 0 : volume / 100;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = (event) => {
      console.error('Speech synthesis error:', event);
      setIsSpeaking(false);
    };
    
    setIsSpeaking(true);
    speechSynthesisRef.current.speak(utterance);
  };

  // Handle volume change
  const handleVolumeChange = (value) => {
    setVolume(value[0]);
    setIsMuted(value[0] === 0);
  };

  // Handle volume mute toggle
  const handleMuteToggle = () => {
    if (isMuted) {
      setIsMuted(false);
    } else {
      setIsMuted(true);
    }
  };

  return (
    <DashboardLayout 
      title="AR Experience"
      description="View and interact with augmented reality scenes"
    >
      <div className="space-y-6">
        {/* Top Controls */}
        <div className="flex flex-col md:flex-row gap-4 justify-between">
          <div className="flex-1 max-w-md">
            <Input
              placeholder="Search AR experiences..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full"
            />
          </div>
          
          <div className="flex gap-2 flex-wrap">
            <Tabs defaultValue="all" onValueChange={setFilter} className="w-full md:w-auto">
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="featured">Featured</TabsTrigger>
                <TabsTrigger value="recent">Recent</TabsTrigger>
                <TabsTrigger value="education">Education</TabsTrigger>
                <TabsTrigger value="design">Design</TabsTrigger>
              </TabsList>
            </Tabs>
            
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="icon">
                  <Settings className="h-4 w-4" />
                  <span className="sr-only">Settings</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>AR Settings</DialogTitle>
                  <DialogDescription>
                    Configure your AR experience preferences
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="high-quality">High Quality Rendering</Label>
                    <Switch id="high-quality" />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="auto-speak">Auto Text-to-Speech</Label>
                    <Switch id="auto-speak" />
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <Label>Performance Mode</Label>
                      <span className="text-sm text-slate-500">Balanced</span>
                    </div>
                    <Slider defaultValue={[50]} max={100} step={1} />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline">Reset to Default</Button>
                  <Button>Save Changes</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            
            <Dialog>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create AR Scene
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Create New AR Scene</DialogTitle>
                  <DialogDescription>
                    Start building a new augmented reality experience
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="scene-name">Scene Name</Label>
                    <Input id="scene-name" placeholder="Enter scene name" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="scene-desc">Description</Label>
                    <Input id="scene-desc" placeholder="Enter scene description" />
                  </div>
                  <div className="space-y-2">
                    <Label>Template</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <Button variant="outline" className="h-auto flex flex-col items-center p-4 justify-start">
                        <Cube className="h-8 w-8 mb-2 text-sky-500" />
                        <span>Blank Scene</span>
                      </Button>
                      <Button variant="outline" className="h-auto flex flex-col items-center p-4 justify-start">
                        <Layers className="h-8 w-8 mb-2 text-indigo-500" />
                        <span>Product Display</span>
                      </Button>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline">Cancel</Button>
                  <Button>Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
        
        {/* Device compatibility notice */}
        {!isCompatible && (
          <Card className="border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800">
            <CardContent className="p-4 flex items-start gap-3">
              <div className="shrink-0">
                <Info className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                  AR Features Limited
                </p>
                <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                  Your device or browser doesn't fully support WebXR. You can view 3D models, but immersive AR experiences require a compatible device.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* AR Scenes Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredScenes.length > 0 ? (
            filteredScenes.map(scene => (
              <motion.div 
                key={scene.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Card className="h-full overflow-hidden hover:shadow-md transition-shadow cursor-pointer border-slate-200 dark:border-slate-700" onClick={() => handleSelectScene(scene)}>
                  <div className="aspect-video relative bg-slate-100 dark:bg-slate-800 overflow-hidden">
                    {/* This would be an actual image in production */}
                    <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-900/80 to-slate-700/80">
                      <Cube className="h-12 w-12 text-white/50" />
                    </div>
                    {scene.status === 'featured' && (
                      <div className="absolute top-2 right-2 bg-amber-500 text-white text-xs py-1 px-2 rounded-full">
                        Featured
                      </div>
                    )}
                  </div>
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg">{scene.title}</CardTitle>
                    </div>
                    <CardDescription className="flex items-center gap-1 text-xs">
                      <span className="flex items-center">
                        <Star className="h-3 w-3 text-amber-500 mr-1" />
                        {scene.rating}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">•</span>
                      <span className="flex items-center">
                        <Users className="h-3 w-3 text-slate-400 mr-1" />
                        {scene.usageCount}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">•</span>
                      <span>{scene.category}</span>
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                      {scene.description}
                    </p>
                  </CardContent>
                  <CardFooter className="border-t border-slate-100 dark:border-slate-800 pt-3">
                    <div className="flex flex-wrap gap-1">
                      {scene.tags.map(tag => (
                        <span 
                          key={tag} 
                          className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full text-slate-600 dark:text-slate-400"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </CardFooter>
                </Card>
              </motion.div>
            ))
          ) : (
            <div className="col-span-3 flex flex-col items-center justify-center py-12 text-center">
              <div className="bg-slate-100 dark:bg-slate-800 rounded-full p-4 mb-4">
                <Cube className="h-8 w-8 text-slate-400" />
              </div>
              <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-1">No AR Scenes Found</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md">
                We couldn't find any AR scenes matching your search criteria. Try adjusting your filters or search query.
              </p>
            </div>
          )}
        </div>
        
        {/* AR Viewer Modal */}
        <Dialog 
          open={selectedScene !== null} 
          onOpenChange={(open) => {
            if (!open) {
              setSelectedScene(null);
              setIsARActive(false);
              setIsSpeaking(false);
              if (speechSynthesisRef.current) {
                speechSynthesisRef.current.cancel();
              }
            }
          }}
        >
          <DialogContent className="sm:max-w-[90vw] max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
            <div className="p-4 md:p-6 border-b border-slate-100 dark:border-slate-800">
              <div className="flex justify-between items-start">
                <div>
                  <DialogTitle className="text-xl">{selectedScene?.title}</DialogTitle>
                  <DialogDescription className="mt-1">
                    {selectedScene?.description}
                  </DialogDescription>
                </div>
                <DialogClose className="rounded-full p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800">
                  <X className="h-4 w-4" />
                </DialogClose>
              </div>
            </div>
            
            <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
              {/* Main AR Viewport */}
              <div className="relative flex-1 min-h-[300px] bg-slate-900 overflow-hidden">
                {isSceneLoading ? (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="flex flex-col items-center">
                      <RefreshCw className="h-8 w-8 text-white animate-spin mb-2" />
                      <p className="text-white text-sm">Loading AR Scene...</p>
                    </div>
                  </div>
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <canvas ref={canvasRef} className="w-full h-full" />
                    
                    {!isARActive && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm">
                        <div className="max-w-md text-center p-6">
                          <motion.div 
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            transition={{ duration: 0.5 }}
                            className="bg-slate-800/80 rounded-2xl p-6 border border-slate-700 shadow-xl"
                          >
                            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center">
                              <Cube className="h-8 w-8 text-white" />
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-2">Ready to Launch AR Experience</h3>
                            <p className="text-slate-300 mb-6">
                              You're about to enter a fully immersive AR environment. For the best experience, ensure you're in a well-lit area with enough space to move around.
                            </p>
                            <div className="flex flex-col sm:flex-row gap-3 justify-center">
                              <Button 
                                variant="outline" 
                                className="border-slate-600 text-slate-200 hover:bg-slate-700 hover:text-white"
                                onClick={() => null}
                              >
                                <Monitor className="h-4 w-4 mr-2" />
                                View 3D Only
                              </Button>
                              <Button 
                                className="bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white"
                                onClick={handleLaunchAR}
                              >
                                <Zap className="h-4 w-4 mr-2" />
                                Launch AR
                              </Button>
                            </div>
                          </motion.div>
                        </div>
                      </div>
                    )}
                    
                    {/* AR Controls (visible when AR is active) */}
                    {isARActive && (
                      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
                        <div className="bg-slate-800/70 backdrop-blur-sm rounded-full py-2 px-4 flex items-center gap-2">
                          <Button variant="ghost" size="icon" className="text-white hover:bg-slate-700">
                            <Pause className="h-5 w-5" />
                          </Button>
                          <Button variant="ghost" size="icon" className="text-white hover:bg-slate-700">
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="text-white hover:bg-slate-700">
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="text-white hover:bg-slate-700">
                            <Share2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Side Panel - Text-to-Speech and Info */}
              <div className="w-full md:w-80 lg:w-96 border-t md:border-t-0 md:border-l border-slate-100 dark:border-slate-800 flex flex-col">
                <Tabs defaultValue="speak" className="flex-1 flex flex-col">
                  <TabsList className="mx-4 mt-4 mb-2">
                    <TabsTrigger value="speak" className="flex-1">
                      <Headphones className="h-4 w-4 mr-2" />
                      Text to Speech
                    </TabsTrigger>
                    <TabsTrigger value="info" className="flex-1">
                      <Info className="h-4 w-4 mr-2" />
                      Details
                    </TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="speak" className="flex-1 flex flex-col p-4 pt-2">
                    <Card className="flex-1 flex flex-col border-slate-200 dark:border-slate-700">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">AR Voice Narration</CardTitle>
                        <CardDescription>Listen to spoken descriptions of the AR elements</CardDescription>
                      </CardHeader>
                      <CardContent className="flex-1 pb-0">
                        <div className="space-y-4">
                          <ScrollArea className="h-32 rounded-md border border-slate-200 dark:border-slate-700 p-4">
                            <p className="text-sm text-slate-600 dark:text-slate-300">
                              {speechText || "No voice narration available yet. Interact with AR elements to generate descriptions."}
                            </p>
                          </ScrollArea>
                          <div className="space-y-4">
                            <div className="flex items-center gap-4">
                              <button
                                onClick={handleMuteToggle}
                                className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                              >
                                {isMuted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
                              </button>
                              <Slider 
                                value={[volume]} 
                                min={0} 
                                max={100} 
                                step={1} 
                                onValueChange={handleVolumeChange}
                                className="flex-1"
                              />
                              <span className="text-xs text-slate-500 dark:text-slate-400 w-8 text-right">
                                {volume}%
                              </span>
                            </div>
                            <Button 
                              onClick={handleSpeak} 
                              disabled={!speechText || (!speechSynthesisRef.current)} 
                              className="w-full"
                            >
                              {isSpeaking ? (
                                <>
                                  <Pause className="h-4 w-4 mr-2" />
                                  Stop Speaking
                                </>
                              ) : (
                                <>
                                  <Play className="h-4 w-4 mr-2" />
                                  Speak Text
                                </>
                              )}
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                      <CardFooter className="pt-4">
                        <div className="w-full text-xs text-slate-500 dark:text-slate-400">
                          <p>Using {deviceType === 'mobile' ? 'mobile' : 'desktop'} speech synthesis engine</p>
                        </div>
                      </CardFooter>
                    </Card>
                  </TabsContent>
                  
                  <TabsContent value="info" className="flex-1 p-4 pt-2">
                    <Card className="border-slate-200 dark:border-slate-700">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Scene Information</CardTitle>
                        <CardDescription>Detailed information about this AR experience</CardDescription>
                      </CardHeader>
                      <CardContent className="pb-0">
                        <div className="space-y-4">
                          <div>
                            <h4 className="text-sm font-medium mb-1">Category</h4>
                            <p className="text-sm text-slate-600 dark:text-slate-400">{selectedScene?.category}</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Tags</h4>
                            <div className="flex flex-wrap gap-1">
                              {selectedScene?.tags.map(tag => (
                                <span 
                                  key={tag} 
                                  className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full text-slate-600 dark:text-slate-400"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Created</h4>
                            <p className="text-sm text-slate-600 dark:text-slate-400">{selectedScene?.createdAt}</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Usage</h4>
                            <p className="text-sm text-slate-600 dark:text-slate-400">Used by {selectedScene?.usageCount} users</p>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium mb-1">Compatibility</h4>
                            <div className="flex flex-wrap gap-2">
                              <div className="flex items-center text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                                <Smartphone className="h-3 w-3 mr-1" />
                                Mobile
                              </div>
                              <div className="flex items-center text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                                <Monitor className="h-3 w-3 mr-1" />
                                Desktop
                              </div>
                              <div className="flex items-center text-xs text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-full">
                                <Wifi className="h-3 w-3 mr-1" />
                                WebXR
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                      <CardFooter className="pt-4">
                        <div className="flex justify-between w-full">
                          <Button variant="outline" size="sm">
                            <MessageSquare className="h-4 w-4 mr-2" />
                            Feedback
                          </Button>
                          <Button variant="outline" size="sm">
                            <ExternalLink className="h-4 w-4 mr-2" />
                            Export
                          </Button>
                        </div>
                      </CardFooter>
                    </Card>
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
} 