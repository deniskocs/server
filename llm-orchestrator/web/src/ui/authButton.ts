import { readKeycloakConfig } from "../auth/keycloakConfig";
import {
  logoutLocally,
  readSessionLabel,
  startKeycloakLogin,
} from "../auth/keycloakAuth";
import { isAuthenticated, subscribeSession } from "../auth/session";

function el<K extends keyof HTMLElementTagNameMap>(
  name: K,
  props?: { className?: string; text?: string }
): HTMLElementTagNameMap[K] {
  const n = document.createElement(name);
  if (props?.className) n.className = props.className;
  if (props?.text) n.textContent = props.text;
  return n;
}

export function mountAuthButton(container: HTMLElement): void {
  const cfg = readKeycloakConfig();
  container.hidden = false;
  if (!cfg) {
    container.replaceChildren(
      el("span", {
        className: "head-auth__user",
        text: "Auth unavailable",
      })
    );
    return;
  }

  const render = (): void => {
    container.replaceChildren();
    if (isAuthenticated()) {
      const wrap = el("div", { className: "head-auth" });
      const label = readSessionLabel();
      if (label) {
        wrap.append(el("span", { className: "head-auth__user", text: label }));
      }
      const logout = el("button", {
        className: "btn btn--login",
        text: "Log out",
      });
      logout.type = "button";
      logout.addEventListener("click", () => {
        logoutLocally();
      });
      wrap.append(logout);
      container.append(wrap);
      return;
    }

    const login = el("button", {
      className: "btn btn--login",
      text: "Log in",
    });
    login.type = "button";
    login.addEventListener("click", () => {
      login.disabled = true;
      void startKeycloakLogin().catch((e) => {
        login.disabled = false;
        console.error(e);
        window.alert(
          e instanceof Error ? e.message : "Could not start Keycloak login"
        );
      });
    });
    container.append(login);
  };

  render();
  subscribeSession(() => render());
}
