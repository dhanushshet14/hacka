# Aetherion AR Frontend

The frontend application for the Aetherion AR platform, built with Next.js and integrating with the backend API.

## Features

- Modern UI with Tailwind CSS and shadcn/ui components
- Responsive design optimized for both desktop and mobile
- Interactive visualizations for AR experience management
- Text processing interface with real-time feedback
- User authentication with JWT
- Dashboard for monitoring and analytics

## Technology Stack

- **Next.js**: React framework for production
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality UI components
- **Framer Motion**: Animation library for smooth transitions
- **React Hook Form**: Form validation and handling

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn

### Installation

1. Clone the repository
2. Navigate to the frontend directory:
   ```
   cd frontend
   ```
3. Install dependencies:
   ```
   npm install
   ```
   or
   ```
   yarn install
   ```

### Development

Run the development server:

```bash
npm run dev
# or
yarn dev
```

Or use the convenience script:

```bash
# Make the script executable first
chmod +x run-frontend.sh

# Run in development mode
./run-frontend.sh
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Building for Production

```bash
npm run build
# or
yarn build
```

Or use the convenience script:

```bash
./run-frontend.sh -m build
```

### Running in Production Mode

```bash
npm run start
# or
yarn start
```

Or use the convenience script:

```bash
./run-frontend.sh -m start
```

## Project Structure

```
frontend/
├── components/          # Reusable UI components
│   ├── ui/              # Base UI components (from shadcn)
│   └── ...              # Custom components
├── pages/               # Page components and routing
│   ├── api/             # API routes
│   ├── dashboard/       # Dashboard pages
│   └── ...              # Other pages
├── public/              # Static assets
├── styles/              # Global styles
├── utils/               # Utility functions and hooks
│   ├── api.js           # API client
│   └── ...              # Other utilities
├── next.config.js       # Next.js configuration
└── tailwind.config.js   # Tailwind CSS configuration
```

## Environment Variables

Create a `.env.local` file in the root directory with the following variables:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Connecting to the Backend

The frontend is configured to connect to the backend API running at `http://localhost:8000/api` by default. You can change this by setting the `NEXT_PUBLIC_API_URL` environment variable.

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

© 2023 Aetherion AR Project. All rights reserved.
