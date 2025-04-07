FROM node:16-alpine
WORKDIR /srv/app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
ENV NODE_ENV=development
RUN npm run build
EXPOSE 1337
CMD ["npm", "run", "develop"]