#
# Do not change content here, image automatically built
#
FROM ${BUILD_FROM}

${DOCKERFILE_BUILDER_ARGS}
${DOCKERFILE_BUILDER_ENVVARS}

RUN if [ ! -d "${BUILDER_TARGETS_FOLDERS_CONTAINER_SETUP}" ]; then \
        mkdir -p ${BUILDER_TARGETS_FOLDERS_CONTAINER_SETUP}; \
    fi \
    && \
    if [ ! -d "${BUILDER_TARGETS_FOLDERS_CONTAINER_CONFIG}" ]; then \
        mkdir -p ${BUILDER_TARGETS_FOLDERS_CONTAINER_CONFIG}; \
    fi

${DOCKERFILE_BUILDER_IMPORTS}

RUN chmod +x -R ${BUILDER_TARGETS_FOLDERS_CONTAINER_BINARIES} && \
    sync && \
    ${BUILDER_TARGETS_CONTAINER_SETUP} 1>/dev/stdout 2>/dev/stderr

${DOCKERFILE_BUILDER_PORTS}
${DOCKERFILE_BUILDER_WORKDIR}

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["${BUILDER_TARGETS_CONTAINER_DOCKER_RUN}"]

LABEL \
    org.label-schema.vcs-ref="$BUILD_COMMIT" \
    org.label-schema.vcs-url="$BUILD_REPO"