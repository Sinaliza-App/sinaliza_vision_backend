const axios = require('axios');
const PYTHON_SERVICE_URL = 'http://127.0.0.1:5000/predict';

const predictSign = async (payload_inteiro) => {
    try {
        // Envia o pacote inteiro (imagem, width, height, stride) pro Python
        const response = await axios.post(PYTHON_SERVICE_URL, payload_inteiro);

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