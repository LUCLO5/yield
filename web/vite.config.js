import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" so the build works at luclo5.github.io/prediction-market-scanner/ or any subpath
export default defineConfig({ plugins: [react()], base: "./" });
