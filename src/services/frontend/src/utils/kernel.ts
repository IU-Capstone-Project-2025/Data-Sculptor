import { ServerConnection } from "@jupyterlab/services";


export const listKernels = async () => {
  const settings = ServerConnection.makeSettings({
    baseUrl: 'http://jh.data-sculptor.ru',
  });

  const response = await ServerConnection.makeRequest(
    `${settings.baseUrl}api/kernelspecs`,
    {},
    settings
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch kernelspecs: ${response.statusText}`);
  }
  const data = await response.json();
  return data.kernelspecs.toString();
};