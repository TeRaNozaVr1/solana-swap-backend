const express = require("express");
const cors = require("cors");

const app = express();
app.use(express.json());

// Дозволяємо CORS для Netlify
app.use(cors({ 
    origin: "https://inquisitive-manatee-aa9f3b.netlify.app",
    methods: "GET,HEAD,PUT,PATCH,POST,DELETE",
    credentials: true
}));

// API для взаємодії з main.py
const PYTHON_API_URL = "https://solana-python-backend.onrender.com/process"; // замініть на реальний URL

const axios = require("axios");

app.post("/send-data", async (req, res) => {
    try {
        const response = await axios.post(PYTHON_API_URL, req.body);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: "Помилка підключення до Python API" });
    }
});

// Запуск сервера
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Node.js сервер працює на порту ${PORT}`));
