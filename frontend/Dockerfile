FROM node:20-alpine

WORKDIR /app

# Copia arquivos de dependências
COPY package.json .

# Instala dependências
RUN npm install

# Copia o código fonte
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
