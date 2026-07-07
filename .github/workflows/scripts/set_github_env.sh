# Helper to set GitHub Actions environment variables

set_github_env() {
	# Inputs (environment variables):
	# - GITHUB_ENV (from GitHub Actions)

	# Inputs (arguments):
	# - var_name: The name of the environment variable to set
	# - var_value: The value of the environment variable to set
	# - is_optional: Whether the variable is optional (default: false)
	#     ('true' or 'optional' means true, anything else means false)
	# - is_secret: Whether the value is secret and should be masked (default: false)
	#     ('true' or 'secret' means true, anything else means false)
	# - is_verbose: Whether to print verbose information (default: false)
	#     ('true' or 'verbose' means true, anything else means false)

	local var_name="$1"
	local var_value="$2"
	local is_optional="$3"
	local is_secret="$4"
	local is_verbose="$5"

	# Normalize boolean inputs
	if [ "${is_optional}" = 'optional' ]; then is_optional='true'; fi
	if [ "${is_secret}" = 'secret' ]; then is_secret='true'; fi
	if [ "${is_verbose}" = 'verbose' ]; then is_verbose='true'; fi

	if [ -z "${var_name}" ]; then
		# Fail on empty variable name
		echo "Error: Variable name is empty" >&2
		return 1
	fi

	if [ -z "${var_value}" ]; then
		if [ "${is_optional}" != "true" ]; then
			# Fail on empty non-optional value
			echo "Error: Variable value is empty" >&2
			return 1
		fi
	elif [ "${is_secret}" = "true" ]; then
		# Mask non-empty secret value
		echo "${var_value}" | sed 's/^ */::add-mask::/'
	fi

	if [ "${is_verbose}" = "true" ]; then
		# Print verbose information
		if [ "${is_secret}" = "true" ]; then
			echo "Set ${var_name} (secret)"
		else
			echo "Set ${var_name} to '${var_value}'"
		fi
	fi

	# Export the GitHub Actions environment variable
	{
		echo "${var_name}<<GITHUB_ENV_EOF"
		echo "${var_value}"
		echo 'GITHUB_ENV_EOF'
	} >> "${GITHUB_ENV}"
}
