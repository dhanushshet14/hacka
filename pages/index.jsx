import React from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

export default function LandingPage() {
  // Animation variants
  const fadeIn = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.6 }
    }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.5 }
    }
  };

  // Feature data
  const features = [
    {
      title: "Agent-based Architecture",
      description: "Multi-agent system for distributed processing and complex task handling",
      icon: "👥"
    },
    {
      title: "Speech Integration",
      description: "Real-time speech-to-text and text-to-speech capabilities for natural interaction",
      icon: "🔊"
    },
    {
      title: "LangGraph Integration",
      description: "Complex workflow orchestration for AI agents with advanced reasoning",
      icon: "🧠"
    }
  ];

  return (
    <div className="flex min-h-screen flex-col">
      <Head>
        <title>Aetherion AR Platform</title>
        <meta name="description" content="Advanced AR platform with AI capabilities" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-800/95 backdrop-blur-sm text-white border-b border-slate-700">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold">A</div>
            <h1 className="text-xl font-bold">Aetherion AR</h1>
          </div>
          <nav>
            <ul className="flex space-x-6">
              <li><Link href="/" className="hover:text-sky-400 transition">Home</Link></li>
              <li><Link href="/dashboard" className="hover:text-sky-400 transition">Dashboard</Link></li>
            </ul>
          </nav>
        </div>
      </header>

      <main className="flex-grow">
        {/* Hero Section */}
        <section className="relative bg-gradient-to-b from-slate-900 to-slate-800 text-white py-20">
          {/* Background elements */}
          <div className="absolute inset-0 overflow-hidden opacity-20">
            <div className="absolute -top-24 -left-24 w-96 h-96 bg-sky-500 rounded-full filter blur-3xl"></div>
            <div className="absolute top-1/2 -right-24 w-96 h-96 bg-indigo-500 rounded-full filter blur-3xl"></div>
          </div>

          <div className="container mx-auto px-4 relative z-10">
            <div className="flex flex-col lg:flex-row items-center gap-12">
              <motion.div 
                className="flex-1 text-center lg:text-left"
                initial="hidden"
                animate="visible"
                variants={fadeIn}
              >
                <h2 className="text-5xl font-bold mb-6">
                  Experience the Future of <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-600">AR</span>
                </h2>
                <p className="text-xl mb-10 max-w-2xl mx-auto lg:mx-0">
                  Aetherion AR leverages cutting-edge AI technologies to provide 
                  seamless integration of digital information into the physical world.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                  <Link href="/dashboard">
                    <Button className="w-full sm:w-auto bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-300 shadow-lg hover:shadow-xl">
                      Go to Dashboard
                    </Button>
                  </Link>
                </div>
              </motion.div>
              
              <motion.div 
                className="flex-1"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2 }}
              >
                <div className="relative h-[400px] w-full max-w-[500px] mx-auto">
                  <div className="absolute inset-0 bg-gradient-to-tr from-sky-500/20 to-indigo-500/20 rounded-xl backdrop-blur-sm border border-white/10"></div>
                  <div className="absolute top-10 left-10 right-10 bottom-10 bg-slate-800/80 rounded-lg shadow-2xl overflow-hidden flex items-center justify-center">
                    <div className="text-center p-6">
                      <div className="text-6xl mb-4">🥽</div>
                      <p className="text-lg font-medium mb-2">AR Experience Preview</p>
                      <p className="text-sm text-slate-400">Interactive demo would appear here</p>
                    </div>
                  </div>
                  <div className="absolute -top-4 -right-4 w-20 h-20 bg-indigo-500/40 rounded-full filter blur-xl"></div>
                  <div className="absolute -bottom-6 -left-6 w-24 h-24 bg-sky-500/40 rounded-full filter blur-xl"></div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-16 bg-white">
          <div className="container mx-auto px-4">
            <motion.div 
              className="text-center mb-12"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 className="text-3xl font-bold text-center mb-6">Key Features</h2>
              <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                Our platform combines advanced AI technologies with AR to create
                transformative experiences for users across industries.
              </p>
            </motion.div>

            <motion.div 
              className="grid md:grid-cols-3 gap-8"
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {features.map((feature, index) => (
                <motion.div key={index} variants={cardVariants}>
                  <Card className="h-full hover:shadow-md transition-shadow duration-300">
                    <CardContent className="p-6">
                      <div className="text-4xl mb-4">{feature.icon}</div>
                      <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                      <p className="text-slate-600">{feature.description}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16 bg-gradient-to-r from-sky-500 to-indigo-600 text-white">
          <div className="container mx-auto px-4 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5 }}
            >
              <h2 className="text-3xl font-bold mb-6">Ready to Get Started?</h2>
              <p className="text-xl mb-10 max-w-2xl mx-auto">
                Join thousands of innovators who are already transforming their work with Aetherion AR.
              </p>
              <div className="flex flex-col sm:flex-row justify-center gap-4">
                <Link href="/dashboard">
                  <Button className="w-full sm:w-auto bg-white text-indigo-600 hover:bg-slate-100 px-6 py-3 rounded-lg font-medium transition-all duration-300">
                    Go to Dashboard
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      <footer className="bg-slate-900 text-white py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex justify-center space-x-6 mb-4">
            <Link href="#" className="text-slate-400 hover:text-white transition-colors">
              <span className="sr-only">Twitter</span>
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84"></path>
              </svg>
            </Link>
            <Link href="#" className="text-slate-400 hover:text-white transition-colors">
              <span className="sr-only">GitHub</span>
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd"></path>
              </svg>
            </Link>
          </div>
          <p>© 2023 Aetherion AR Project. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
} 