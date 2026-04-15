# PoseTracker Backend

Node.js backend for PoseTracker application with PostgreSQL + pgvector.

## Tech Stack
- **Node.js** + **TypeScript**
- **Express.js** (Web Framework)
- **Prisma** (ORM)
- **PostgreSQL** + **pgvector** (Database)
- **Cloudinary** (Media Storage)
- **JWT** (Authentication)

## Getting Started

### Prerequisites
- Node.js 18+ 
- PostgreSQL 14+ with pgvector extension
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Update .env with your database credentials
```

### Database Setup

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# Open Prisma Studio (optional)
npm run prisma:studio
```

### Development

```bash
# Start development server
npm run dev
```

### Production

```bash
# Build the project
npm run build

# Start production server
npm start
```

## API Endpoints

- `GET /health` - Health check endpoint

## Environment Variables

See `.env.example` for required environment variables.
