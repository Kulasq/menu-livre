const CONFIG = {
  // Em produção (Nginx proxy), API fica no mesmo domínio — sem prefixo
  // Em desenvolvimento local, aponta para o uvicorn direto
  API_URL: window.location.hostname === 'localhost' ? 'http://localhost:8000' : '',

  // Chave usada no localStorage
  STORAGE_KEYS: {
    CARRINHO:  'ml_carrinho',
    CLIENTE:   'ml_cliente',
    TOKEN:     'ml_token',
  },
};