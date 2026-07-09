const axios = require('axios');
const pythonUrl = process.env.PYTHON_API_URL || 'http://localhost:5000';

const predictSign = async (payload_inteiro) => {
    try {
        // Envia o pacote inteiro (imagem, width, height, stride) pro Python
        const response = await axios.post(pythonUrl + '/predict', payload_inteiro);

        return {
            prediction: response.data.prediction,
            confidence: response.data.confidence
        };
    } catch (error) {
        console.error("Erro ao comunicar com o serviço Python:", error.message);
        throw new Error('Falha no serviço de visão computacional');
    }
};
module.exports = { predictSign };