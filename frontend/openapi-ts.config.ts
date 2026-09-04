import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: process.env.OPENAPI_INPUT ?? "./openapi.json",
  output: "./src/client",

  plugins: [
    "@hey-api/client-axios",
    {
      name: "@hey-api/sdk",
      client: "@hey-api/client-axios",
      operations: {
        strategy: "byTags",
        containerName: "{{name}}Service",
        methods: "static",
        nesting: "operationId",
        methodName: (name) => {
          const [, ...parts] = name.split(/[-_./]/)
          return parts
            .map((part, index) =>
              index === 0 ? part : part.charAt(0).toUpperCase() + part.slice(1),
            )
            .join("")
        },
      },
    },
    {
      name: "@hey-api/schemas",
      type: "json",
    },
  ],
})
