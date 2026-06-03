FROM nginx:alpine

COPY src/frontend/ /usr/share/nginx/html/
COPY deploy/interfaz/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
