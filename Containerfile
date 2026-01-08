# Use Red Hat Universal Base Image 9
FROM registry.access.redhat.com/ubi9/ubi:latest

LABEL maintainer="Miguel Angel Ajo Pelayo <miguelangel@ajo.es>"
LABEL description="PhotoSort - Photo inbox management tool"

# Install EPEL repository for exiftool
RUN dnf install -y \
    https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm \
    && dnf install -y epel-release \
    && dnf install -y \
    perl-Image-ExifTool \
    python3.11 \
    python3.11-pip \
    && dnf clean all

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install photosort and dependencies using uv
RUN uv sync --frozen

# Create default config directory
RUN mkdir -p /etc/photosort

# Set entrypoint to use uv run
ENTRYPOINT ["uv", "run", "photosort"]
CMD ["--help"]
