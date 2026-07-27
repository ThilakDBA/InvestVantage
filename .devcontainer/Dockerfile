FROM mcr.microsoft.com/devcontainers/python:1-3.13-bookworm

# The upstream image currently carries a Yarn APT source whose signing key is
# unavailable. Devcontainer features run apt-get update, so remove that unused
# source before Docker-in-Docker and GitHub CLI features are installed.
RUN rm -f \
    /etc/apt/sources.list.d/yarn.list \
    /etc/apt/sources.list.d/yarn.sources
