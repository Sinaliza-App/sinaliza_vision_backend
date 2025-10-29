const jwt = require('jsonwebtoken');

// Este é o nosso "segurança"
const authMiddleware = (req, res, next) => {
  // 1. O Flutter deve enviar o token no cabeçalho 'Authorization'
  //    no formato: "Bearer SEU_TOKEN_JWT_AQUI"
  const authHeader = req.headers['authorization'];
  
  // 2. Pegar o token do cabeçalho
  const token = authHeader && authHeader.split(' ')[1]; // Pega só o token, sem o "Bearer "

  // 3. Se não veio token, o usuário não está logado
  if (token == null) {
    return res.status(401).json({ message: 'Acesso negado. Nenhum token fornecido.' }); // 401 Unauthorized
  }

  // 4. Verificar se o "crachá" (token) é válido
  try {
    // jwt.verify vai checar a assinatura e a data de expiração
    const payload = jwt.verify(token, process.env.JWT_SECRET);

    // 5. Se o token é válido, ANEXAMOS os dados do usuário (o payload)
    //    na requisição (req) para que a próxima rota possa usá-los.
    req.user = payload;
    
    // 6. Deixa a requisição continuar para a rota final (ex: /users/me)
    next(); 

  } catch (ex) {
    // 7. Se o token é inválido ou expirado
    res.status(400).json({ message: 'Token inválido.' }); // 400 Bad Request
  }
};

module.exports = authMiddleware;