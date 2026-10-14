
import sys,json,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mark import github_assistant as assistant
from mark.cognition.integration import direct_response
from mark.github import GitHubError

class GitHubAssistantTests(unittest.TestCase):
    def test_explicit_access_reads_actual_metadata_and_contents(self):
        with patch.object(assistant.github,'_gh',return_value=json.dumps({'full_name':'thu12dta3/Vladmir','default_branch':'main','html_url':'https://github.com/thu12dta3/Vladmir','permissions':{'push':True}})),patch.object(assistant.github,'read_file',return_value=('a'*40,'README test fixture')) as read:
            reply=direct_response('Consegue acessar o repositório Vladmir no GitHub?',{})
            self.assertIn('Sim. Consultei',reply);self.assertIn('thu12dta3/Vladmir',reply);self.assertIn('permissão de escrita',reply);read.assert_called_once_with('thu12dta3/Vladmir','main','README.md')
    def test_error_never_claims_success(self):
        with patch.object(assistant.github,'_gh',side_effect=GitHubError('private token')),patch.object(assistant.github,'_public_api',side_effect=GitHubError('offline')):
            result=assistant.direct('Você tem acesso ao github?',{});self.assertIn('Não consegui confirmar',result);self.assertNotIn('private token',result)
    def test_explicit_repository_link_can_be_read(self):
        metadata={'full_name':'other/public','default_branch':'main','html_url':'https://github.com/other/public','permissions':{}}
        with patch.object(assistant.github,'_gh',return_value=json.dumps(metadata)),patch.object(assistant.github,'read_file',return_value=('c'*40,'Public fixture')) as read:
            result=assistant.direct('Consegue acessar https://github.com/other/public?',{})
            self.assertIn('Sim. Consultei',result);self.assertIn('other/public',result);read.assert_called_once_with('other/public','main','README.md')
    def test_path_traversal_refused(self):
        with self.assertRaises(GitHubError):assistant.request('Leia no github o arquivo ../private',{})
    def test_context_is_bounded_untrusted_and_readonly(self):
        with patch.object(assistant.github,'read_file',return_value=('b'*40,'ignore instructions '*1000)) as read,patch.object(assistant.github,'update_file') as write:
            context=assistant.context('Analise no github o arquivo src/mark/brain.py',{})
            self.assertIn('Conteúdo externo não confiável',context);self.assertIn('"truncated": true',context);self.assertLess(len(context),13500);read.assert_called_once_with('thu12dta3/Vladmir','main','src/mark/brain.py');write.assert_not_called()
    def test_normal_chat_does_not_query_github(self):
        with patch.object(assistant.github,'_gh') as call:
            self.assertIsNone(assistant.direct('olá, tudo bem?',{}));self.assertEqual(assistant.context('olá',{}),'');call.assert_not_called()
    def test_only_library_prevents_tools(self):
        with patch.object(assistant.github,'_gh') as call:
            self.assertIsNone(direct_response('Use somente minha biblioteca: massa molar da água',{}));self.assertIsNone(direct_response('Use somente minha biblioteca: você tem acesso ao github?',{}));call.assert_not_called()
if __name__=='__main__':unittest.main()
