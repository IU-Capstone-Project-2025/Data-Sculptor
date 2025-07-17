FROM openjdk:17-jdk-slim

# install Postgres client+server, curl, unzip
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    postgresql postgresql-client curl unzip \
 && rm -rf /var/lib/apt/lists/*

# install Keycloak 21.x
ENV KC_VERSION=21.0.2 \
    KC_HOME=/opt/keycloak
RUN curl -fsSL https://github.com/keycloak/keycloak/releases/download/${KC_VERSION}/keycloak-${KC_VERSION}.zip -o /tmp/kc.zip \
 && mkdir -p ${KC_HOME} \
 && unzip /tmp/kc.zip -d /opt \
 && mv /opt/keycloak-${KC_VERSION}/* ${KC_HOME}/ \
 && rm -rf /tmp/kc.zip

# make dirs
RUN mkdir -p /var/lib/postgresql/data

WORKDIR /

# copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# expose the Keycloak ports (inside container)
EXPOSE 8080 8443

# data persistence points
VOLUME [ "/var/lib/postgresql/data", "/opt/keycloak/data" ]

ENTRYPOINT ["/entrypoint.sh"]

