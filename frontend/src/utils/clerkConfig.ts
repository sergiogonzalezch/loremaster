/** Clave pública de Clerk leída desde variables de entorno.
 *  Definida → modo Clerk (demo/production). Undefined → modo local. */
export const clerkKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as
  | string
  | undefined;
