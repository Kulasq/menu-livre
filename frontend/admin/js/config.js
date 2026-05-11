const CONFIG = {
  // Em produção (Nginx proxy), API fica no mesmo domínio — sem prefixo
  // Em desenvolvimento local, aponta para o uvicorn direto
  API_URL: window.location.hostname === 'localhost' ? 'http://localhost:8000' : '',

  STORAGE: {
    ACCESS_TOKEN: 'ml_admin_access_token',
    REFRESH_TOKEN: 'ml_admin_refresh_token',
    USUARIO_NOME: 'ml_admin_usuario_nome',
    USUARIO_ROLE: 'ml_admin_usuario_role',
  },

  // Paths relativos sem .html — funciona em dev (/admin/) e em prod (raiz do domínio)
  // Nginx usa try_files $uri $uri.html para resolver sem extensão
  PAGINAS: {
    LOGIN: '.',
    DASHBOARD: 'dashboard.html',
    CARDAPIO: 'cardapio.html',
    PEDIDOS: 'pedidos.html',
    CLIENTES: 'clientes.html',
    CUPONS: 'cupons.html',
  },
}