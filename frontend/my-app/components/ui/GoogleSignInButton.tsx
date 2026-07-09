"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { googleLogin, getMe } from "@/lib/api";
import { resolvePostLoginPath, type MeResponse } from "@/lib/auth";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleIdConfig) => void;
          renderButton: (parent: HTMLElement, options: GoogleButtonOptions) => void;
        };
      };
    };
  }
}

interface GoogleIdConfig {
  client_id: string;
  callback: (response: { credential: string }) => void;
}

interface GoogleButtonOptions {
  theme?: "outline" | "filled_blue" | "filled_black";
  size?: "large" | "medium" | "small";
  width?: number;
  text?: "signin_with" | "signup_with" | "continue_with";
  shape?: "rectangular" | "pill" | "circle" | "square";
}

type GoogleSignInButtonProps = {
  onError?: (message: string) => void;
};

export default function GoogleSignInButton({ onError }: GoogleSignInButtonProps) {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load script Google Identity Services if not already loaded
    if (!document.getElementById("google-identity-script")) {
      const script = document.createElement("script");
      script.id = "google-identity-script";
      script.src = "https://accounts.google.com/gsi/client?hl=en";
      script.async = true;
      script.defer = true;
      script.onload = initGoogle;
      document.body.appendChild(script);
    } else {
      initGoogle();
    }

    function initGoogle() {
      if (!window.google || !buttonRef.current) return;

      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
        callback: handleCredentialResponse,
      });

      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: "filled_black",
        size: "large",
        width: 384,
        text: "signin_with",
        shape: "pill",
      });
    }

    async function handleCredentialResponse(response: { credential: string }) {
      try {
        await googleLogin(response.credential);
        const me = (await getMe()) as MeResponse;
        router.replace(resolvePostLoginPath(me.data));
        router.refresh();
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Sign in with Google failed";
        onError?.(message);
        console.error("Error connecting when signing in with Google", err);
      }
    }
  }, [router, onError]);

  return <div ref={buttonRef} />;
}