const express = require("express");
const cors = require("cors");
const fetch = require("node-fetch");

const GEMINI_API_KEY = process.env.GEMINI_API_KEY; // Sua chave Gemini em variável de ambiente no Render

const app = express();
app.use(cors());
app.use(express.json());

app.post("/generate-audio", async (req, res) => {
  try {
    const { text, style, voice } = req.body;
    if (!text || !style || !voice) {
      return res.status(400).json({ error: "Dados incompletos." });
    }

    // Chamada para Gemini TTS
    const geminiResponse = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-tts:generateContent?key=" + GEMINI_API_KEY,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [
                { text: `${style}\n\n${text}` }
              ]
            }
          ],
          generationConfig: { temperature: 1 },
          tools: [],
          responseMimeType: "audio/wav",
          voice: { name: voice }
        }),
      }
    );

    const data = await geminiResponse.json();

    // Procura o audio gerado:
    const part = data.candidates?.[0]?.content?.parts?.[0];
    if (!part?.inlineData?.data) {
      // Mostra mensagem de erro detalhada se vier do Gemini:
      console.error("Erro Gemini:", JSON.stringify(data));
      return res.status(500).json({ error: "Falha ao gerar áudio.", details: data });
    }

    res.json({
      audio_data: part.inlineData.data, // base64 WAV
      model_used: "pro"
    });
  } catch (err) {
    console.error("ERRO NO BACKEND:", err); // <-- Agora mostra erro no log do Render
    res.status(500).json({ error: String(err) });
  }
});

app.get("/", (req, res) => {
  res.send("API do Painel de Locutores funcionando!");
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log("Servidor backend do Painel de Locutores rodando na porta", PORT);
});
