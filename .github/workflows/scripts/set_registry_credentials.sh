# Helper to set Docker registry credentials as GitHub Actions environment variables

set_registry_credentials() {
	# Inputs (environment variables):
	# - REGISTRY_URL (required)
	#     The Docker registry URL (e.g., docker.io)
	# - REGISTRY_USERNAME (required)
	#     The Docker registry username
	# - REGISTRY_TOKEN (required)
	#     The Docker registry token or password
	# - REGISTRY_NAMESPACE (optional)
	#     The Docker registry namespace to use (e.g., organization or user)
	#     (defaults to registry username if not set)
	# - IMAGES_PREFIX (optional)
	#     The prefix to use for image names (e.g., project name)
	#     (defaults to repository name if not set)
	# - IMAGES_SUFFIX (optional)
	#     The suffix to use for image names (e.g., service name)
	# - REPOSITORY_OWNER (required)
	#     The owner of the repository (e.g., GitHub repository owner)
	# - REPOSITORY_PATH (required)
	#     The full path of the repository (e.g., GitHub repository path)

	# Inputs (arguments):
	# - registry_url_env_name
	#     The environment variable name to save the registry URL as (e.g, DHCR_URL)
	# - registry_images_prefix_env_name
	#     The environment variable name to save the images prefix as (e.g, DHCR_IMAGES_PREFIX)
	# - registry_username_env_name
	#     The environment variable name to save the registry username as (e.g, DHCR_USERNAME)
	# - registry_token_env_name
	#     The environment variable name to save the registry token as (e.g, DHCR_TOKEN)

	# Outputs (environment variables):
	# - ${registry_images_prefix_env_name}
	#	  The Docker images prefix to use for pushing images
	# - ${registry_username_env_name}
	#	  The Docker registry username
	# - ${registry_token_env_name}
	#	  The Docker registry token or password

	# Verify set_github_env helper is available
	if ! command -v set_github_env >/dev/null 2>&1; then
		echo "Error: set_github_env helper is not available" >&2
		exit 1
	fi

	local registry_url_env_name="$1"
	local registry_images_prefix_env_name="$2"
	local registry_username_env_name="$3"
	local registry_token_env_name="$4"

	# Verify REGISTRY_URL variable
	if [ -z "${REGISTRY_URL}" ]; then
		echo "Error: Registry URL is not set" >&2
		exit 1
	fi

	# Build REGISTRY_IMAGES_PREFIX variable
	# Include registry URL
	REGISTRY_URL="$(echo "${REGISTRY_URL}" | tr '[:upper:]' '[:lower:]')"
	REGISTRY_IMAGES_PREFIX="${REGISTRY_URL}"
	# Include registry namespace
	if [ -n "${REGISTRY_NAMESPACE}" ] && [ "${REGISTRY_NAMESPACE}" != "0" ] && [ "${REGISTRY_NAMESPACE}" != "NONE" ]; then
		if [ "${REGISTRY_NAMESPACE}" = "REGISTRY_USERNAME" ]; then
			# Use the registry username as namespace
			REGISTRY_NAMESPACE="${REGISTRY_USERNAME}"
		elif [ "${REGISTRY_NAMESPACE}" = "REPOSITORY_OWNER" ] || [ "${REGISTRY_NAMESPACE}" = "1" ]; then
			# Use the repository owner as namespace
			REGISTRY_NAMESPACE="${REPOSITORY_OWNER}"
		fi
		REGISTRY_NAMESPACE="$(echo "${REGISTRY_NAMESPACE}" | tr '[:upper:]' '[:lower:]')"
		REGISTRY_IMAGES_PREFIX="${REGISTRY_IMAGES_PREFIX}/${REGISTRY_NAMESPACE}"
	fi
	# Include images prefix (or default to repository name)
	if [ -n "${IMAGES_PREFIX}" ]; then
		IMAGES_PREFIX="$(echo "${IMAGES_PREFIX}" | tr '[:upper:]' '[:lower:]')"
	else
		IMAGES_PREFIX="$(echo "${REPOSITORY_PATH##*/}" | tr '[:upper:]' '[:lower:]')"
	fi
	REGISTRY_IMAGES_PREFIX="${REGISTRY_IMAGES_PREFIX}/${IMAGES_PREFIX}"
	# Include images suffix
	if [ -n "${IMAGES_SUFFIX}" ] && [ "${IMAGES_SUFFIX}" != "0" ] && [ "${IMAGES_SUFFIX}" != "NONE" ]; then
		IMAGES_SUFFIX="$(echo "${IMAGES_SUFFIX}" | tr '[:upper:]' '[:lower:]')"
		REGISTRY_IMAGES_PREFIX="${REGISTRY_IMAGES_PREFIX}${IMAGES_SUFFIX}"
	fi

	# Verify REGISTRY_USERNAME variable
	if [ -z "${REGISTRY_USERNAME}" ]; then
		echo "Error: Registry username is not set" >&2
		exit 1
	fi

	# Verify REGISTRY_TOKEN variable
	if [ -z "${REGISTRY_TOKEN}" ]; then
		echo "Error: Registry token is not set" >&2
		exit 1
	fi

	# Set GitHub Actions environment variables
	set_github_env "${registry_url_env_name}" "${REGISTRY_URL}" non-optional secret verbose
	set_github_env "${registry_images_prefix_env_name}" "${REGISTRY_IMAGES_PREFIX}" non-optional secret verbose
	set_github_env "${registry_username_env_name}" "${REGISTRY_USERNAME}" non-optional secret verbose
	set_github_env "${registry_token_env_name}" "${REGISTRY_TOKEN}" non-optional secret verbose
}
