import { GoogleLogin } from "@react-oauth/google";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export function GoogleLoginButton() {
  const { loginWithGoogle } = useAuth();

  return (
    <GoogleLogin
      onSuccess={(credentialResponse) => {
        if (!credentialResponse.credential) return;
        loginWithGoogle(credentialResponse.credential).catch(() => {
          toast.error("Sign-in failed. Please try again.");
        });
      }}
      onError={() => toast.error("Google sign-in was cancelled or failed.")}
    />
  );
}
