import "@/styles/globals.css";
import type { AppProps } from "next/app";
import Head from "next/head";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>CCTV Sentinel — AI Violence Monitoring</title>
        <meta name="description" content="AI CCTV Central Monitoring & Violence Incident Management System" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <div className="min-h-screen bg-sentinel-bg text-gray-100 flex flex-col">
        <Component {...pageProps} />
      </div>
    </>
  );
}
