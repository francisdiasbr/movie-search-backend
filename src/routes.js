const express = require('express');
const axios = require('axios');
const OpenAI = require('openai');

const router = express.Router();

router.get('/search', async (req, res) => {
  const { query } = req.query;
  try {
    
    const openai = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });

    const aiResponse = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        { role: 'system', content: 'You are a helpful assistant.' },
        { role: 'user', content: `Sugira filmes baseados na seguinte pesquisa: ${query}` }
      ],
      max_tokens: 1000,
    });

    console.log('AI Response:', aiResponse);

    if (aiResponse.choices && aiResponse.choices.length > 0) {
      const choice = aiResponse.choices[0];
      console.log('First Choice:', choice);

      if (choice.message && choice.message.content) {
        const searchQuery = choice.message.content.trim();
        console.log('Search Query:', searchQuery);

        const tmdbResponse = await axios.get(`https://api.themoviedb.org/3/search/movie`, {
          params: {
            api_key: process.env.TMDB_API_KEY,
            query: searchQuery
          }
        });

        res.json(tmdbResponse.data.results);
      } else {
        res.status(500).json({ error: 'Invalid response format from OpenAI' });
      }
    } else {
      res.status(500).json({ error: 'No choices returned from OpenAI' });
    }
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;