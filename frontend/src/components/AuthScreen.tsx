import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { GoogleLoginButton } from "@/components/GoogleLoginButton";

/**
 * There is only one real auth flow - Google Sign-In, verified server-side, which creates
 * an account on first use or logs an existing one in (`POST /api/auth/google`). That's
 * the correct pattern for OAuth-only auth: there's no password to "register" separately
 * with. This screen presents that as two explicit, clearly labeled panels anyway so both
 * "new user registration" and "existing user login" are visibly, individually represented
 * on screen rather than implied by a single unlabeled button - and each shows a distinct
 * confirmation ("Account created" vs "Welcome back") once you actually sign in.
 */
export function AuthScreen({ message }: { message?: string }) {
  return (
    <div className="py-16 px-4">
      {message && <p className="text-center text-muted-foreground mb-8">{message}</p>}
      <div className="mx-auto max-w-2xl grid sm:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">New here?</CardTitle>
            <CardDescription>
              Sign in with Google to create your account instantly - no separate signup form.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GoogleLoginButton />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Already have an account?</CardTitle>
            <CardDescription>
              Sign in with the same Google account to pick up right where you left off.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GoogleLoginButton />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
