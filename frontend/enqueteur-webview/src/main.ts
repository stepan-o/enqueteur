import "./styles/app.css";
import { mountAppFlow } from "./app/appFlow";

const app = document.getElementById("app");
if (!app) throw new Error("#app not found");

mountAppFlow({
    mountEl: app,
});
