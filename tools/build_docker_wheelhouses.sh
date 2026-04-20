#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_IMAGE="${DOCKER_IMAGE:-ubuntu:latest}"
PLATFORMS="${PLATFORMS:-linux/amd64 linux/arm64}"
HOST_UID="${HOST_UID:-$(id -u)}"
HOST_GID="${HOST_GID:-$(id -g)}"
BUILDER_IMAGE_BASE="${BUILDER_IMAGE_BASE:-ragent-wheelhouse-builder}"
BUILDER_IMAGE_VERSION="${BUILDER_IMAGE_VERSION:-ubuntu24.04-py3.12}"
BUILD_BUILDER_IMAGE="${BUILD_BUILDER_IMAGE:-auto}"
proxy_build_args=()
proxy_run_args=()

docker_proxy_value() {
  printf '%s' "$1" | sed -E 's#(://)(127\.0\.0\.1|localhost)([:/])#\1host.docker.internal\3#g'
}

for proxy_var in \
  http_proxy \
  https_proxy \
  all_proxy \
  HTTP_PROXY \
  HTTPS_PROXY \
  ALL_PROXY \
  no_proxy \
  NO_PROXY; do
  if [ -n "${!proxy_var:-}" ]; then
    proxy_value="$(docker_proxy_value "${!proxy_var}")"
    proxy_build_args+=(--build-arg "$proxy_var=$proxy_value")
    proxy_run_args+=(-e "$proxy_var=$proxy_value")
  fi
done

platform_arch() {
  case "$1" in
    linux/amd64) echo "amd64" ;;
    linux/arm64) echo "arm64" ;;
    *) echo "${1#*/}" | tr '/' '-' ;;
  esac
}

builder_image_for_platform() {
  echo "$BUILDER_IMAGE_BASE:$BUILDER_IMAGE_VERSION-$(platform_arch "$1")"
}

ensure_builder_image() {
  local platform="$1"
  local image="$2"
  local -a docker_build_cmd

  if [ "$BUILD_BUILDER_IMAGE" = "never" ]; then
    return
  fi

  if [ "$BUILD_BUILDER_IMAGE" = "auto" ] && docker image inspect "$image" >/dev/null 2>&1; then
    return
  fi

  docker_build_cmd=(
    docker build
    --platform "$platform"
    --build-arg "BASE_IMAGE=$DOCKER_IMAGE"
  )
  if [ "${#proxy_build_args[@]}" -gt 0 ]; then
    docker_build_cmd+=("${proxy_build_args[@]}")
  fi
  docker_build_cmd+=(
    -f "$PROJECT_ROOT/tools/docker/wheelhouse-builder.Dockerfile"
    -t "$image"
    "$PROJECT_ROOT"
  )
  "${docker_build_cmd[@]}"
}

for platform in $PLATFORMS; do
  declare -a docker_run_cmd
  builder_image="$(builder_image_for_platform "$platform")"
  echo "ensuring builder image for $platform: $builder_image"
  ensure_builder_image "$platform" "$builder_image"

  echo "building wheelhouse for $platform with $builder_image"
  docker_run_cmd=(
    docker run --rm
    --platform "$platform"
    -e HOST_UID="$HOST_UID"
    -e HOST_GID="$HOST_GID"
  )
  if [ "${#proxy_run_args[@]}" -gt 0 ]; then
    docker_run_cmd+=("${proxy_run_args[@]}")
  fi
  docker_run_cmd+=(
    -v "$PROJECT_ROOT:/work"
    -w /work
    "$builder_image"
    bash -lc '
      set -euo pipefail
      PYTHON_BIN=/opt/ragent-wheelhouse-venv/bin/python tools/build_wheelhouse.sh
      chown -R "$HOST_UID:$HOST_GID" /work/vendor/wheelhouse /work/.runtime
    '
  )
  "${docker_run_cmd[@]}"
done
