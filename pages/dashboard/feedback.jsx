import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import DashboardLayout from '@/layouts/DashboardLayout';
import { useToast } from '@/components/ui/use-toast';
import { StarRating } from '@/components/ui/star-rating';
import { VoiceRecorder } from '@/components/voice-recorder';
import { feedbackAPI, arAPI } from '@/utils/api';
import { useForm } from '@/utils/useForm';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Send,
  MessageSquare,
  Clock,
  ChevronRight,
  Star,
  ThumbsUp,
  Mic,
  History,
  AlertCircle,
  CheckCircle,
  Info,
  RefreshCw,
  X,
} from 'lucide-react';

export default function FeedbackPage() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('new');
  const [arExperiences, setArExperiences] = useState([]);
  const [submittedFeedback, setSubmittedFeedback] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [voiceRecording, setVoiceRecording] = useState(null);
  const [voiceTranscription, setVoiceTranscription] = useState('');
  const [submissionSuccess, setSubmissionSuccess] = useState(false);
  const [feedbackTags, setFeedbackTags] = useState([
    'User Interface', 'Performance', 'Content Quality', 
    'Accuracy', 'Ease of Use', 'Visual Design', 
    'Audio Quality', 'Responsiveness', 'Engagement'
  ]);
  const [error, setError] = useState(null);

  // Create form with validation
  const { 
    values, 
    errors, 
    isSubmitting,
    handleChange, 
    handleSubmit, 
    setFieldValue, 
    resetForm 
  } = useForm({
    initialValues: {
      experienceId: '',
      rating: 0,
      title: '',
      details: '',
      improvements: '',
      includeSuggestions: false,
      tags: [],
      type: 'general'
    },
    validate: (values) => {
      const errors = {};
      if (!values.experienceId) errors.experienceId = 'Please select an AR experience';
      if (!values.rating) errors.rating = 'Please provide a rating';
      if (!values.title) errors.title = 'Please provide a title for your feedback';
      if (!values.details) errors.details = 'Please provide some feedback details';
      return errors;
    },
    onSubmit: handleFeedbackSubmit
  });

  // Fetch AR experiences and feedback history
  useEffect(() => {
    const fetchExperiences = async () => {
      try {
        setLoading(true);
        const experiences = await arAPI.getScenes();
        setArExperiences(experiences || []);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch AR experiences:', err);
        setError('Failed to load AR experiences. Please try again.');
        // Fallback data
        setArExperiences([
          { id: 1, title: 'Medical Anatomy Explorer' },
          { id: 2, title: 'Manufacturing Process Visualization' },
          { id: 3, title: 'Architectural Design Preview' },
          { id: 4, title: 'Solar System Explorer' },
          { id: 5, title: 'Product Showcase Demo' },
          { id: 6, title: 'Molecular Structure Viewer' }
        ]);
      } finally {
        setLoading(false);
      }
    };

    fetchExperiences();
  }, []);

  // Get feedback history when active tab changes
  useEffect(() => {
    if (activeTab === 'history') {
      fetchFeedbackHistory();
    }
  }, [activeTab]);

  // Fetch feedback history
  const fetchFeedbackHistory = async () => {
    try {
      setLoadingHistory(true);
      const history = await feedbackAPI.getFeedbackHistory();
      setSubmittedFeedback(history || []);
      setLoadingHistory(false);
    } catch (error) {
      console.error('Error fetching feedback history:', error);
      setLoadingHistory(false);
    }
  };

  // Handle feedback form submission
  async function handleFeedbackSubmit(formValues) {
    try {
      // Create feedback data
      const feedbackData = {
        ...formValues,
        timestamp: new Date().toISOString(),
        hasVoiceFeedback: !!voiceRecording
      };
      
      // Add voice recording if available
      if (voiceRecording) {
        // In a real app, you would upload the voice file to a server
        // For this demo, we'll just add a placeholder
        feedbackData.voiceRecording = voiceRecording;
      }
      
      // Submit feedback to API
      await feedbackAPI.submitFeedback(feedbackData);
      
      // Show success animation and message
      setSubmissionSuccess(true);
      
      toast({
        title: "Feedback Submitted",
        description: "Thank you for your valuable input!",
      });
      
      // Reset form after a delay
      setTimeout(() => {
        resetForm();
        setVoiceRecording(null);
        setVoiceTranscription('');
        setSubmissionSuccess(false);
      }, 2000);
      
    } catch (error) {
      console.error('Error submitting feedback:', error);
      toast({
        variant: "destructive",
        title: "Submission Error",
        description: "There was a problem submitting your feedback. Please try again.",
      });
    }
  }
  
  // Handle voice feedback recording
  const handleVoiceRecordingComplete = (recording, transcript) => {
    setVoiceRecording(recording);
    if (transcript) {
      setVoiceTranscription(transcript);
      setFieldValue('details', transcript);
    }
  };

  // Find experience by ID
  const getExperienceName = (id) => {
    const experience = arExperiences.find(exp => exp.id === id);
    return experience ? experience.title : 'Unknown Experience';
  };

  // Handle tag toggle
  const handleTagToggle = (tag) => {
    const currentTags = values.tags || [];
    if (currentTags.includes(tag)) {
      setFieldValue('tags', currentTags.filter(t => t !== tag));
    } else {
      setFieldValue('tags', [...currentTags, tag]);
    }
  };

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring", stiffness: 100 }
    }
  };

  return (
    <DashboardLayout
      title="Feedback"
      description="Submit feedback on your AR experience"
    >
      <div className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="new">New Feedback</TabsTrigger>
            <TabsTrigger value="history">Feedback History</TabsTrigger>
          </TabsList>

          {/* New Feedback Tab */}
          <TabsContent value="new" className="space-y-6">
            {submissionSuccess ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center justify-center p-8"
              >
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ 
                    type: "spring", 
                    stiffness: 260, 
                    damping: 20,
                    delay: 0.1 
                  }}
                  className="w-20 h-20 mb-4 rounded-full bg-green-100 flex items-center justify-center text-green-600"
                >
                  <CheckCircle className="w-10 h-10" />
                </motion.div>
                <h2 className="text-xl font-bold text-center mb-2">Feedback Submitted!</h2>
                <p className="text-center text-slate-600 dark:text-slate-400 max-w-md mb-6">
                  Thank you for your valuable feedback. Your input helps us improve the AR experience.
                </p>
                <Button onClick={() => setSubmissionSuccess(false)}>
                  Submit Another
                </Button>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Submit Feedback</CardTitle>
                    <CardDescription>
                      Share your experience with our AR application
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Experience Selection */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="experienceId">AR Experience</FormLabel>
                      <Select
                        name="experienceId"
                        value={values.experienceId}
                        onValueChange={(value) => setFieldValue('experienceId', value)}
                      >
                        <SelectTrigger id="experienceId" className="w-full">
                          <SelectValue placeholder="Select AR Experience" />
                        </SelectTrigger>
                        <SelectContent>
                          {loading ? (
                            <div className="flex items-center justify-center p-4">
                              <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                              <span>Loading experiences...</span>
                            </div>
                          ) : arExperiences.length > 0 ? (
                            arExperiences.map((experience) => (
                              <SelectItem key={experience.id} value={experience.id}>
                                {experience.title}
                              </SelectItem>
                            ))
                          ) : (
                            <div className="flex items-center justify-center p-4 text-slate-500">
                              No experiences available
                            </div>
                          )}
                        </SelectContent>
                      </Select>
                      {errors.experienceId && (
                        <p className="text-sm text-red-500">{errors.experienceId}</p>
                      )}
                    </div>

                    {/* Type of feedback */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="type">Type of Feedback</FormLabel>
                      <Select
                        name="type"
                        value={values.type}
                        onValueChange={(value) => setFieldValue('type', value)}
                      >
                        <SelectTrigger id="type">
                          <SelectValue placeholder="Select type of feedback" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="general">General Feedback</SelectItem>
                          <SelectItem value="bug">Bug Report</SelectItem>
                          <SelectItem value="feature">Feature Request</SelectItem>
                          <SelectItem value="improvement">Improvement Suggestion</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Rating */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="rating">Overall Rating</FormLabel>
                      <div>
                        <StarRating
                          value={values.rating}
                          onChange={(rating) => setFieldValue('rating', rating)}
                          className="mb-1"
                        />
                        <p className="text-xs text-slate-500">
                          {values.rating > 0 
                            ? values.rating === 5 
                              ? "Excellent! Exceeded expectations" 
                              : values.rating >= 4 
                                ? "Very good experience" 
                                : values.rating >= 3 
                                  ? "Satisfactory experience" 
                                  : values.rating >= 2 
                                    ? "Needs improvement" 
                                    : "Poor experience"
                            : "Click to rate"
                          }
                        </p>
                      </div>
                      {errors.rating && (
                        <p className="text-sm text-red-500">{errors.rating}</p>
                      )}
                    </div>

                    {/* Feedback Tags */}
                    <div className="space-y-2">
                      <FormLabel>Feedback Tags</FormLabel>
                      <div className="flex flex-wrap gap-2">
                        {feedbackTags.map((tag) => (
                          <Badge
                            key={tag}
                            variant={values.tags?.includes(tag) ? "default" : "outline"}
                            className="cursor-pointer"
                            onClick={() => handleTagToggle(tag)}
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {/* Title */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="title">Title</FormLabel>
                      <Input
                        id="title"
                        name="title"
                        value={values.title}
                        onChange={handleChange}
                        placeholder="Brief summary of your feedback"
                      />
                      {errors.title && (
                        <p className="text-sm text-red-500">{errors.title}</p>
                      )}
                    </div>

                    {/* Details */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="details">Details</FormLabel>
                      <Textarea
                        id="details"
                        name="details"
                        value={values.details}
                        onChange={handleChange}
                        placeholder="Please provide detailed information about your experience"
                        rows={4}
                      />
                      {errors.details && (
                        <p className="text-sm text-red-500">{errors.details}</p>
                      )}
                    </div>

                    {/* Voice Feedback */}
                    <div className="space-y-2">
                      <FormLabel>Voice Feedback (Optional)</FormLabel>
                      <VoiceRecorder onRecordingComplete={handleVoiceRecordingComplete} />
                      {voiceTranscription && (
                        <div className="mt-2 p-3 bg-slate-50 rounded-md border border-slate-200">
                          <p className="text-sm text-slate-500 mb-1">Transcription:</p>
                          <p className="text-sm">{voiceTranscription}</p>
                        </div>
                      )}
                    </div>

                    {/* Improvements */}
                    <div className="space-y-2">
                      <FormLabel htmlFor="improvements">Suggested Improvements (Optional)</FormLabel>
                      <Textarea
                        id="improvements"
                        name="improvements"
                        value={values.improvements}
                        onChange={handleChange}
                        placeholder="Any specific suggestions for improvements?"
                        rows={3}
                      />
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={resetForm}
                    >
                      Reset
                    </Button>
                    <Button 
                      type="submit" 
                      disabled={isSubmitting}
                      className="gap-2"
                    >
                      {isSubmitting && <RefreshCw className="h-4 w-4 animate-spin" />}
                      Submit Feedback
                    </Button>
                  </CardFooter>
                </Card>
              </form>
            )}
          </TabsContent>

          {/* Feedback History Tab */}
          <TabsContent value="history" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Your Feedback History</CardTitle>
                <CardDescription>
                  Review and track your previously submitted feedback
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingHistory ? (
                  <div className="flex items-center justify-center p-8">
                    <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                    <span>Loading feedback history...</span>
                  </div>
                ) : submittedFeedback.length > 0 ? (
                  <div className="space-y-4">
                    {submittedFeedback.map((feedback, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                      >
                        <Card className="overflow-hidden">
                          <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-800/50">
                            <div className="flex items-center">
                              <div className="mr-4 flex-shrink-0">
                                <div className="w-10 h-10 rounded-full bg-sky-100 dark:bg-sky-900/30 flex items-center justify-center">
                                  <MessageSquare className="h-5 w-5 text-sky-600 dark:text-sky-400" />
                                </div>
                              </div>
                              <div>
                                <h3 className="text-sm font-medium">{feedback.title}</h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400">
                                  {getExperienceName(feedback.experienceId)}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center">
                              <div className="flex mr-4" aria-label={`Rating: ${feedback.rating} out of 5 stars`}>
                                {[...Array(5)].map((_, i) => (
                                  <Star
                                    key={i}
                                    className={`h-4 w-4 ${
                                      i < feedback.rating
                                        ? 'text-amber-500 fill-amber-500'
                                        : 'text-slate-300 dark:text-slate-600'
                                    }`}
                                  />
                                ))}
                              </div>
                              <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center">
                                <Clock className="h-3 w-3 mr-1" />
                                {new Date(feedback.timestamp).toLocaleDateString()}
                              </div>
                            </div>
                          </div>
                          <CardContent className="p-4">
                            <p className="text-sm text-slate-600 dark:text-slate-300">
                              {feedback.details}
                            </p>
                            {feedback.improvements && (
                              <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                                <h4 className="text-xs font-medium mb-1 text-slate-500 dark:text-slate-400">
                                  Improvement Suggestions:
                                </h4>
                                <p className="text-sm text-slate-600 dark:text-slate-300">
                                  {feedback.improvements}
                                </p>
                              </div>
                            )}
                            {feedback.hasVoiceFeedback && (
                              <Badge variant="outline" className="mt-3 flex items-center w-fit">
                                <Mic className="h-3 w-3 mr-1" />
                                Voice feedback included
                              </Badge>
                            )}
                          </CardContent>
                          {feedback.response && (
                            <div className="p-4 bg-slate-50 dark:bg-slate-800/30 border-t border-slate-100 dark:border-slate-800">
                              <h4 className="text-xs font-medium mb-2 text-slate-500 dark:text-slate-400 flex items-center">
                                <ThumbsUp className="h-3 w-3 mr-1" />
                                Response from Team:
                              </h4>
                              <p className="text-sm text-slate-600 dark:text-slate-300">
                                {feedback.response}
                              </p>
                            </div>
                          )}
                        </Card>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center p-8">
                    <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 dark:bg-slate-800">
                      <History className="h-8 w-8 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-medium mb-2">No Feedback History</h3>
                    <p className="text-slate-500 dark:text-slate-400 max-w-md mx-auto mb-6">
                      You haven't submitted any feedback yet. Your feedback history will appear here.
                    </p>
                    <Button onClick={() => setActiveTab('new')}>
                      Submit Feedback
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
} 