const cors = require("cors");

// Дозволити запити з Netlify
const corsOptions = {
    origin: "https://your-netlify-app.netlify.app", // Замість цього вкажіть ваш домен на Netlify
    methods: "GET,POST,OPTIONS",
    allowedHeaders: "Content-Type,Authorization"
};
app.use(cors(corsOptions));
