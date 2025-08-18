import { Field, PanelSection, PanelSectionRow, Spinner } from "@decky/ui";
import { FC, useState } from "react";
import { FaCheck, FaTimes } from "react-icons/fa";
import { ActionButtonItem } from "./ActionButtonItem";
import { backend, ResourceType } from "../backend";
import { t } from 'i18next';
import { L } from "../i18n";
import { toaster } from "@decky/api";
import { DeckyNatpierceIcon } from "../global";

export interface InstallationGuideProps {
  coreVersion: string;
  refreshCallback: () => any;
  quitCallback: () => any;
}

export const InstallationGuide: FC<InstallationGuideProps> = (props) => {
  const [coreInstalling, setCoreInstalling] = useState(false);

  const installCore = async () => {
    setCoreInstalling(true);
    const [success, error] =
      await backend.upgrade(ResourceType.CORE, await backend.getLatestVersion(ResourceType.CORE));
    setCoreInstalling(false);
    if (!success)
      toaster.toast({
        title: t(L.INSTALL_FAILURE),
        body: `Natpierce: ${error}`,
        icon: <DeckyNatpierceIcon />,
      });
  };

  return (
    <PanelSection title={t(L.INSTALLATION_GUIDE)}>
      <div style={{ margin: '4px 0' }}>
        {t(L.INSTALLATION_MSG)}
      </div>
      <PanelSectionRow>
        <Field
          label="Natpierce"
          onClick={() => installCore().then(props.refreshCallback)}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {coreInstalling ? (<Spinner style={{ width: '1.1em' }} />) : (
                props.coreVersion === "" ? (<FaTimes />) :
                  (<>{props.coreVersion} <FaCheck /></>)
            )}
          </div>
        </Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <ActionButtonItem onClick={props.quitCallback}>
          {props.coreVersion !== "" &&
            t(L.INSTALLATION_FINISH)
          }
        </ActionButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};
