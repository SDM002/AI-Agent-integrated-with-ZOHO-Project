import { Sora, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-plus-jakarta-sans",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata = {
  title: "Zoho Voice Logger | Skysecure Technologies",
  description: "AI-powered Voice Logger for Zoho Projects",
};

export default function RootLayout({ children }) {
  const envScript = `window.__RUNTIME_ENV__ = ${JSON.stringify({
    BACKEND_URL: process.env.BACKEND_URL,
    FETCH_TIMEOUT_MS: process.env.FETCH_TIMEOUT_MS,
    FETCH_RETRY_DELAY_MS: process.env.FETCH_RETRY_DELAY_MS,
  })};`;

  return (
    <html lang="en" className={`h-full ${sora.variable} ${plusJakartaSans.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: envScript }} />
      </head>
      <body className="h-full">
        {children}
      </body>
    </html>
  );
}
