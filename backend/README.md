# MegaLoja Online API
Fornece as principais funções do e-commerce MegaLoja online.

## Estrutura da API
| Camada         | Responsabilidade                                                                      |
|----------------|---------------------------------------------------------------------------------------|
| `routes`       | Receber requisições HTTP e devolver respostas HTTP.                                   |
| `schemas`      | Definir os formatos de entrada e saída da API.                                        |
| `models`       | Representar as entidades e estruturas de dados do domínio e da persistência.          |
| `services`     | Implementar os casos de uso e as regras de negócio.                                   |
| `repositories` | Abstrair operações de persistência e consultas ao banco.                              |
| `integrations` | Comunicar-se com sistemas externos, como gateways de pagamento e serviços de estoque. |

## Entidades do Domínio
| Entidade    | Responsabilidade                                            |
|-------------|-------------------------------------------------------------|
| `Customer`  | Representa o cliente que realiza a compra.                  |
| `Product`   | Representa um produto comercializado.                       |
| `Store`     | Representa uma unidade física da loja.                      |
| `Inventory` | Representa a disponibilidade de produtos em uma unidade.    |
| `Order`     | Representa uma compra realizada.                            |
| `OrderItem` | Representa um produto e sua quantidade dentro de um pedido. |
| `Payment`   | Representa a operação financeira associada ao pedido.       |
| `Pickup`    | Representa as informações referentes à retirada.            |

# Referências de desenvolvimento:
1.  https://pydevtools.com/handbook/tutorial/getting-started-with-uv/
2.  https://pydevtools.com/handbook/how-to/how-to-translate-pip-commands-to-uv/

# Como rodar o MVP
```bash
cd backend
uv sync
uv run api            # http://127.0.0.1:8000 (front servido da pasta /docs do repo)  |  /docs (Swagger da API)
PYTHONPATH=src uv run pytest
```

## Escopo do MVP (Click & Collect)
Persistência em memória (reinicia ao subir) e integrações simuladas (`integrations/`): ERP, gateway de pagamento e notificações. Sem autenticação.

| UC | Endpoint |
|----|----------|
| UC001 Fazer compra | `GET /products`, `POST /orders` |
| UC002 Escolher retirada | `POST /pickup/options` (recomenda a loja mais próxima com estoque) |
| UC003 Acompanhar | `GET /orders?email=`, `GET /orders/{id}/status` |
| UC004 Código de retirada | campo `pickup_code` do pedido |
| UC005 Separar | `GET /stores/{id}/orders`, `POST /orders/{id}/start-preparing` |
| UC006 Pronto | `POST /orders/{id}/ready` |
| UC007 Validar e entregar | `POST /stores/{id}/pickup/validate` |
| UC008 Gerenciar pedidos | `GET /stores/{id}/orders?status=` |
| UC009 Pagamento | `integrations/payment.py` (token `recusado` simula recusa) |
| UC010/UC011 Estoque | `integrations/erp.py` (reserva, baixa, liberação) |
| UC012 Notificar | `integrations/notifications.py`, `GET /orders/{id}/notifications` |

Fora do MVP: autenticação, banco de dados, capacidade/horários de retirada, pedido não retirado (expiração), pagamento real.

## Publicação (GitHub Pages + API)
O repositório fica assim: `backend/` (API FastAPI) e `docs/` (front estático).
1. **API:** suba no Render (`render.yaml` na raiz já está pronto: New → Blueprint). Anote a URL, ex.: `https://megaloja-api.onrender.com`.
2. **Front:** edite `docs/config.js` e coloque essa URL em `window.API_BASE`.
3. **GitHub Pages:** Settings → Pages → Deploy from a branch → `main` / pasta `/docs`.

Obs.: no plano grátis do Render a API "dorme" e a primeira chamada pode demorar ~1 min. Os dados são em memória e zeram quando ela reinicia.
