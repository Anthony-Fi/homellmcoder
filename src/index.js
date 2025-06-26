// Application entry point
console.log('Starting HomeLLMCoder Application');
console.log(`Running on ${process.platform} ${process.arch}`);
console.log(`Node.js version: ${process.version}`);

// Simple web server setup
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files from the public directory
app.use(express.static(path.join(__dirname, '..', 'public')));

// Basic route
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>HomeLLMCoder</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 40px; 
                    text-align: center;
                }
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    background-color: #f9f9f9;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to HomeLLMCoder</h1>
                <p>Your offline desktop application is running successfully!</p>
                <p>Platform: ${process.platform} ${process.arch}</p>
                <p>Node.js: ${process.version}</p>
                <p>Server running on port ${PORT}</p>
            </div>
        </body>
        </html>
    `);
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down gracefully...');
    process.exit(0);
});
