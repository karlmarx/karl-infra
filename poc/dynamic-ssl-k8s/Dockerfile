# Alpine-based JRE image to match the user's stack ("Alpine-based Docker containers").
# The fat jar is built on the host with `mvn package` (see scripts/run-demo.sh) and copied in,
# which keeps the image build fast and offline-friendly. A multi-stage Maven build is fine too.
FROM eclipse-temurin:21-jre-alpine

# No extra packages needed: the demo script reaches the in-pod control API with Alpine's
# built-in busybox `wget` via `kubectl exec`. The app makes its own outbound HTTPS calls.

WORKDIR /app
COPY target/dynamic-ssl-poc.jar /app/app.jar

# APP_MODE selects caller vs origin at runtime (see App.java).
ENV APP_MODE=caller
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
