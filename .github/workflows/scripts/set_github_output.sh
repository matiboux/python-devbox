# Helper to set GitHub Actions job output variables

set_github_output() {
	# Inputs (environment variables):
	# - GITHUB_OUTPUT (from GitHub Actions)

	# Inputs (arguments):
	# - var_name: The name of the environment variable to set
	# - var_value: The value of the environment variable to set
	# - is_optional: Whether the variable is optional (default: false)
	#     ('true' or 'optional' means true, anything else means false)
	# - is_verbose: Whether to print verbose information (default: false)
	#     ('true' or 'verbose' means true, anything else means false)

	local var_name="$1"
	local var_value="$2"
	local is_optional="$3"
	local is_verbose="$4"

	# Normalize boolean inputs
	if [ "${is_optional}" = 'optional' ]; then is_optional='true'; fi
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
	fi

	if [ "${is_verbose}" = "true" ]; then
		# Print verbose information
		echo "Set ${var_name} to '${var_value}'"
	fi

	# Export the GitHub Actions job output variable
	{
		echo "${var_name}<<GITHUB_OUTPUT_EOF"
		echo "${var_value}"
		echo 'GITHUB_OUTPUT_EOF'
	} >> "${GITHUB_OUTPUT}"
}
