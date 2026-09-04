import { createContext, useContext, useState, type ReactNode } from "react";
import { getSavedCity, saveCity } from "./utils";

interface CityCtx {
  city: string;
  setCity: (c: string) => void;
}

const CityContext = createContext<CityCtx | null>(null);

export function CityProvider({ children }: { children: ReactNode }) {
  const [city, setCityState] = useState(getSavedCity());

  function setCity(c: string) {
    setCityState(c);
    saveCity(c);
  }

  return <CityContext.Provider value={{ city, setCity }}>{children}</CityContext.Provider>;
}

export function useCity() {
  const ctx = useContext(CityContext);
  if (!ctx) throw new Error("useCity must be used inside CityProvider");
  return ctx;
}
