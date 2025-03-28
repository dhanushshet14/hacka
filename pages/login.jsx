import React, { useState, useEffect, useContext } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { motion } from 'framer-motion';
import { AuthContext } from '@/utils/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useForm } from '@/utils/useForm';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useContext(AuthContext);
  const [authError, setAuthError] = useState('');
  
  // Auto-redirect to dashboard on page load
  useEffect(() => {
    router.push('/dashboard');
  }, [router]);
  
  const { values, errors, loading, handleChange, handleSubmit } = useForm({
    initialValues: {
      email: '',
      password: ''
    },
    validate: (values) => {
      const errors = {};
      return errors; // No validation needed since we're auto-redirecting
    },
    onSubmit: async (values) => {
      // Auto redirect in useEffect
      router.push('/dashboard');
    }
  });

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 0.5,
        when: "beforeChildren",
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
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col items-center justify-center p-4">
      <Head>
        <title>Redirecting | Aetherion AR</title>
        <meta name="description" content="Redirecting to dashboard" />
      </Head>

      <motion.div 
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="w-full max-w-md"
      >
        <motion.div variants={itemVariants} className="mb-8 text-center">
          <Link href="/" className="inline-block">
            <div className="flex items-center justify-center gap-2">
              <div className="h-10 w-10 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold">A</div>
              <h1 className="text-2xl font-bold text-white">Aetherion AR</h1>
            </div>
          </Link>
        </motion.div>

        <Card className="border border-slate-700 bg-slate-800/50 backdrop-blur-sm shadow-xl">
          <CardHeader>
            <CardTitle className="text-xl text-white">Redirecting</CardTitle>
            <CardDescription className="text-slate-300">Taking you to the dashboard...</CardDescription>
          </CardHeader>

          <CardContent className="flex justify-center py-8">
            <div className="flex items-center justify-center">
              <svg className="animate-spin mr-2 h-8 w-8 text-sky-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          </CardContent>

          <CardFooter className="flex justify-center border-t border-slate-700 bg-slate-800/30">
            <motion.p variants={itemVariants} className="text-sm text-slate-300">
              If you're not redirected,{' '}
              <Link href="/dashboard" className="text-sky-400 hover:text-sky-300 transition-colors font-medium">
                click here
              </Link>
            </motion.p>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
} 