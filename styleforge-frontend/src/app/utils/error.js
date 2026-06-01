/**
 * Parses API error response and returns a structured, human-readable error.
 * Handles both Standard Error and Validation Error (422) formats.
 * 
 * @param {any} errorObj The raw error data parsed from response JSON.
 * @param {string} fallbackMsg Fallback message if parsing fails.
 * @returns {{ message: string, code: string, fields?: Array<{field: string, message: string}> }}
 */
export function parseApiError(errorObj, fallbackMsg = "An unexpected error occurred.") {
  if (!errorObj) {
    return { message: fallbackMsg, code: "unknown_error" };
  }

  // 1. Handle Validation Error Payload (422)
  if (
    errorObj.code === "validation_error" &&
    Array.isArray(errorObj.fields) &&
    errorObj.fields.length > 0
  ) {
    const formattedFields = errorObj.fields
      .map((f) => `${f.field}: ${f.message}`)
      .join(", ");
    return {
      message: formattedFields || errorObj.detail || "Validation failed.",
      code: "validation_error",
      fields: errorObj.fields,
    };
  }

  // 2. Handle Standard Error Payload
  if (errorObj.detail) {
    return {
      message: errorObj.detail,
      code: errorObj.code || "api_error",
    };
  }

  // 3. Simple message string fallback
  if (typeof errorObj === "string") {
    return { message: errorObj, code: "error" };
  }

  return { message: fallbackMsg, code: "unknown_error" };
}
